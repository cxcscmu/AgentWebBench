"""
ContentAgent: LLM agent for website-specific document retrieval.
"""
import os
import re
import time
import json
from typing import List, Tuple, Optional
from awbench.utils.awbench_api import search as awbench_search
from awbench.prompts import summary_reminder_prompt
from awbench.prompts.content_agent import content_agent_prompt_base
from awbench.utils.token_calculator import tokenize
from awbench.agents.llm_client import get_llm_client, call_llm, MODEL_MAX_INPUT_TOKENS
from awbench.agents.base import BaseAgent
import traceback
import random

ACTIONS = ['search', 'answer', 'summary']
MAX_CONTEXT_LENGTH = 8000

class ContentAgent(BaseAgent):
    """
    LLM agent responsible for retrieving documents from a specific website.
    Each agent manages one website and can optimize queries and retrieval strategies.
    """

    ACTIONS = ACTIONS


    def __init__(self, website: str, website_description: str = "No description available", model_name: str = None, log_dir: Optional[str] = None, question_id: Optional[str] = None, llm_config: dict = None):
        self.website = website
        self.website_description = website_description
        self.log_dir = log_dir
        self.question_id = question_id
        
        # Determine API type and model from llm_config or use defaults
        if llm_config:
            self.api_type = llm_config.get("api_type", "gemini")
            self.model_name = llm_config.get("model_id") or model_name or "gemini-2.5-flash"
            self.url = llm_config.get("url")
        else:
            # Default to Gemini for backward compatibility
            self.api_type = "gemini"
            self.model_name = model_name or "gemini-2.5-flash"
            self.url = None
        
        # Setup logging
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            # Create log file for this agent with question_id in filename
            # Format (new, supports multiple requests per question):
            #   content_agent_{website_safe}_{question_id}_{session_id}.log
            # Legacy format (still supported by analysis code):
            #   content_agent_{website_safe}_{question_id}.log
            website_safe = website.replace('.', '_').replace('/', '_')
            # Use timestamp as a deterministic session id so that
            # multiple requests for the same (question_id, website)
            # produce separate log files instead of overwriting.
            session_id = time.strftime("%Y%m%d%H%M%S")
            self.agent_log_file = os.path.join(
                self.log_dir,
                f"content_agent_{website_safe}_{question_id}_{session_id}.log",
            )

            # Write mode: create new file for each question_id (no append, each question gets fresh file)
            session_header = f"ContentAgent Log for {website}\n"
            session_header += f"QUESTION_ID: {question_id if question_id else 'UNKNOWN'}\n"
            session_header += f"API Type: {self.api_type}\n"
            session_header += f"Model: {self.model_name}\n"
            session_header += f"Website Description: {website_description}\n"
            session_header += f"Session Start: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            session_header += "=" * 80 + "\n\n"
            
            with open(self.agent_log_file, 'w', encoding='utf-8') as f:
                f.write(session_header)
                f.flush()
        else:
            self.agent_log_file = None
        
        # Initialize client using unified LLM client
        self.client, self.model_name = get_llm_client(self.api_type, self.model_name, self.url)
        self._log(f"{self.api_type} client initialized successfully (model: {self.model_name})", "INFO")

        # Cache of doc_id -> doc_text from search results (used by _validate_and_get_documents)
        self._doc_cache: dict = {}

        # Reminder configuration (default values, can be overridden)
        self.search_reminder_turn = 5
        self.final_answer_reminder_turn = 10
        self.final_answer_turn = 15

    def _parse_answer_action(self, answer_content: str) -> Tuple[str, List[str]]:
        """
        Parse the <answer> action content to extract summary and documents.
        
        Args:
            answer_content: content inside <answer> tags (should be JSON)
        
        Returns:
            (summary, documents) tuple where documents is a list of document IDs
        """
        summary = ""
        documents = []
        
        try:
            # Try to parse as JSON
            answer_data = json.loads(answer_content)
            if isinstance(answer_data, dict):
                summary = answer_data.get("summary", "")
                documents = answer_data.get("documents", [])
                if not isinstance(documents, list):
                    documents = []
        except (json.JSONDecodeError, TypeError):
            print(f"Error parsing answer content: {str(answer_content)}")
            # If not valid JSON, try to extract from text
            # Look for summary field
            summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', answer_content)
            if summary_match:
                summary = summary_match.group(1)
            
            # Look for documents array
            docs_match = re.search(r'"documents"\s*:\s*\[(.*?)\]', answer_content, re.DOTALL)
            if docs_match:
                docs_str = docs_match.group(1)
                # Extract document IDs (handling both quoted and unquoted)
                doc_ids = re.findall(r'["\']?([^,"\']+)["\']?', docs_str)
                documents = [doc_id.strip() for doc_id in doc_ids if doc_id.strip()]
        
        return summary, documents
    
    def _validate_and_get_documents(self, doc_ids: List[str]) -> List[dict]:
        """
        Return document texts for the given doc_ids using the search result cache.

        Only doc_ids that were returned by a prior _execute_search call are accepted;
        anything else is treated as hallucinated and silently skipped.

        Args:
            doc_ids: List of document IDs to retrieve (at most 3 returned).

        Returns:
            List of {"doc_id": ..., "doc_text": ...} dicts.
        """
        valid_docs = []
        for doc_id in doc_ids:
            doc_id_str = str(doc_id).strip()
            if doc_id_str in self._doc_cache:
                doc_text = self._doc_cache[doc_id_str]
                valid_docs.append({"doc_id": doc_id_str, "doc_text": doc_text})
                self._log(f"Retrieved document {doc_id_str} from cache ({len(doc_text)} chars)")
                if len(valid_docs) >= 3:
                    break
            else:
                self._log(f"Document {doc_id_str} not in search cache, skipping", "WARNING")
        return valid_docs
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message to the agent log file if logging is enabled."""
        if self.agent_log_file:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            qid_prefix = f"[QID:{self.question_id}] " if self.question_id else ""
            with open(self.agent_log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {qid_prefix}[{level}] {message}\n")
                f.flush()  # Ensure immediate write
            
    def _log_session_end(self):
        """Log session end marker."""
        if self.agent_log_file:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            qid_info = f" (QID: {self.question_id})" if self.question_id else ""
            with open(self.agent_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"[{timestamp}] SESSION END{qid_info}\n")
                f.write("=" * 80 + "\n")
                f.flush()
    
    def _execute_search(self, query: str, num_docs: int) -> str:
        """Execute search action: search documents from the website via the AgentWebBench API."""
        start_time = time.time()
        self._log(f"Executing search action for query: {query}")

        results = awbench_search(query, k=num_docs, website=self.website)

        # Populate cache so _validate_and_get_documents can look up texts later.
        for r in results:
            self._doc_cache[r["doc_id"]] = r["doc_text"]

        doc_texts = [{"doc_id": r["doc_id"], "doc_text": r["doc_text"]} for r in results]
        elapsed_time = time.time() - start_time
        self._log(f"Retrieved {len(doc_texts)} documents in {elapsed_time:.2f}s")

        # Return the raw JSON string; the caller wraps it in <information>...</information>.
        return json.dumps(doc_texts, indent=4)
    
    def _execute_response(self, action: Optional[str], num_docs: int) -> Tuple[bool, bool, str, str]:
        """
        Execute the action and return observation.

        Args:
            action: action to be executed, None if format is not correct
            num_docs: Number of documents to retrieve

        Returns:
            done: whether the task is done
            need_update_history: whether need to update the history to agent summary
            next_obs: next observation
            action_type: the type of action executed
        """
        if action is None:
            next_obs = 'An invalid action, cannot be executed.'
            return False, False, next_obs, ''

        action_type, content = self._parse_action(action)
        if action_type not in ACTIONS:
            raise ValueError(f"Invalid action: {action_type}")

        next_obs = ''
        done = False
        need_update_history = False

        if action_type == 'search':
            search_query = content if content else ''
            search_results = self._execute_search(search_query, num_docs)
            observation = f'<information>{search_results}</information>'
            next_obs += observation
        
        elif action_type == "answer":
            done = True
            next_obs += 'Answer generated, the process is done.'
        
        elif action_type == 'summary':
            next_obs += 'You performed a summary action in this turn. The content of this action is ignored since your history turns information has been updated according to it.\n'
            need_update_history = True
        
        return done, need_update_history, next_obs, action_type
    
    def _update_input(self, agent_input: str, cur_response: str, next_obs: str, need_update_history: bool, original_prompt: str, turn_id: int, summary_history: str = '', consecutive_search_cnt: int = 0) -> str:
        """Update the input with the history.
        Args:
            agent_input: current input
            cur_response: current full response
            next_obs: next observation
            need_update_history: whether update the history to agent summary
            original_prompt: original prompt for the question
            turn_id: current turn number
            summary_history: summary content if need_update_history is True
            consecutive_search_cnt: number of consecutive search actions
        Returns:
            updated input
        """
        if need_update_history:
            context = f"[Turn 0 - Turn {turn_id - 1}]:\n{summary_history}\n\n"
            context += f"[Turn {turn_id}]:\n{next_obs}\n\n"
            new_input = original_prompt + context
        else:
            context = f"[Turn {turn_id}]:\n{cur_response}\n{next_obs}\n\n"
            new_input = agent_input + context

        # add reminder for search and final report
        if turn_id == self.final_answer_turn:
            new_input += f'\nNote: You have performed {turn_id} turns. Please output the final report/answer.'
        else:
            if turn_id > self.final_answer_reminder_turn:
                new_input += f'\nNote: You have performed {turn_id} turns. Please consider output the final report. If you still want to search, make sure you check history search results and DO NOT perform duplicate search.'
            if consecutive_search_cnt > self.search_reminder_turn:
                new_input += f'\nNote: You have performed {consecutive_search_cnt} search actions. Please consider update your report scripts or output the final report. If you still want to search, make sure you check history search results and DO NOT perform duplicate search.'
            
            # add summary reminder prompt if context is too long
            input_length = tokenize(new_input)
            if input_length > MAX_CONTEXT_LENGTH:
                new_input += summary_reminder_prompt

        return new_input
    
    def retrieve_documents(self, question: str, num_docs: int, max_turns: int = 5) -> dict:
        """
        Main method: agent retrieves documents for the website.

        Args:
            question: User question
            num_docs: Number of documents to retrieve
            max_turns: Maximum number of agent turns

        Returns:
            A dict with keys "website", "summary", and optionally "documents"
            (a list of {"doc_id": ..., "doc_text": ...} dicts).
        """
        start_time = time.time()
        self._log(f"Starting document retrieval for question: {question}")
        self._log(f"Max turns: {max_turns}")
        if self.question_id:
            self._log(f"Question ID: {self.question_id}")
        
        # Build original prompt
        original_prompt = content_agent_prompt_base.format(
            website=self.website,
            website_description=self.website_description,
            question=question
        )
        
        agent_input = original_prompt

        # Initialize counters for this retrieval session
        consecutive_search_cnt = 0
        
        for turn in range(max_turns):
            turn_start_time = time.time()
            turn_id = turn + 1
            self._log(f"\n--- Turn {turn_id}/{max_turns} ---")
            
            # Query LLM using unified call_llm function
            llm_start_time = time.time()
            self._log(f"Sending prompt to LLM (API: {self.api_type}, model: {self.model_name})")
            self._log(f"LLM Input (length={len(agent_input)}):\n{agent_input}")

            # Check prompt tokens and log warning if exceeds limit
            max_input_tokens = MODEL_MAX_INPUT_TOKENS.get(self.model_name)
            if max_input_tokens is None:
                raise ValueError(f"Model {self.model_name} not found in MODEL_MAX_INPUT_TOKENS")
            prompt_tokens = tokenize(agent_input)
            if prompt_tokens > max_input_tokens:
                warning_msg = f"Truncated prompt due to token limit: Model: {self.model_name}, Max input tokens: {max_input_tokens}, Prompt tokens: {prompt_tokens}"
                self._log(warning_msg, "WARNING")
            
            max_try_times = 5
            response_text = None
            thought = None
            for attempt in range(max_try_times):
                try:
                    response_text, thought = call_llm(
                        self.api_type,
                        self.client,
                        self.model_name,
                        agent_input,
                    )
                    break
                except Exception as e:
                    self._classify_llm_error(e)

                    if attempt == max_try_times - 1:
                        print(f"Failed to get response after {max_try_times} tries: {e}")
                        print(traceback.format_exc())
                        response_text = None
                        thought = None
                    else:
                        time.sleep(random.randint(1, 3))
                        
            
            llm_elapsed = time.time() - llm_start_time
            self._log(f"LLM response received in {llm_elapsed:.2f}s")
            
            if not response_text:
                self._log("No text response from LLM", "WARNING")
                break
            
            # Add thought if available
            if thought is not None and len(thought) > 0:
                original_response = f'<think>{thought}</think>\n{response_text}'
            else:
                original_response = response_text if response_text is not None else ''

            self._log(f"LLM Response: {original_response}")
            
            # Parse actions
            action = self._postprocess_response(response_text)
            if action is None:
                self._log("No valid actions parsed from response, break the loop", "WARNING")
                break

            self._log(f"Parsed action: {action}")
            
            # Execute actions
            done, need_update_history, next_obs, action_type = self._execute_response(
                action, num_docs
            )
            
            # Update consecutive search counter
            if action_type == 'search':
                consecutive_search_cnt += 1
            elif action_type in ['summary', 'answer']:
                consecutive_search_cnt = 0
            
            self._log(f"Action executed. Done: {done}, Need update history: {need_update_history}, Consecutive search count: {consecutive_search_cnt}")
            self._log(f"Next observation: {next_obs[:200]}...")
            
            if done:
                # Agent is done, parse answer action
                self._log("Agent marked as done")
                action_type, answer_content = self._parse_action(action)
                summary, documents = self._parse_answer_action(answer_content)
                
                # Format final result: summary + relevant documents
                result = {"website": self.website}
                
                # Add summary
                if summary:
                    result["summary"] = summary
                    self._log(f"Summary extracted: {summary[:200]}...")
                
                # Validate and get document texts
                if documents:
                    self._log(f"Validating {len(documents)} document IDs...")
                    doc_parts = self._validate_and_get_documents(documents)
                    
                    if doc_parts:
                        result["documents"] = doc_parts
                        self._log(f"Retrieved {len(doc_parts)} valid documents out of {len(documents)} provided")
                    else:
                        self._log(f"No valid documents found from {len(documents)} provided document IDs", "WARNING")
                
                if result.get("summary") is None:
                    result["summary"] = "No relevant information found."

                elapsed_time = time.time() - start_time
                self._log(f"Retrieval completed successfully in {elapsed_time:.2f}s")
                self._log(f"Final result:\n{result}")
                self._log(f"Final result length: {len(json.dumps(result, indent=4))} chars")
                self._log_session_end()
                return result
            
            # Update input for next turn
            summary_content = ''
            if need_update_history:
                # Extract summary content from action
                action_type, summary_content = self._parse_action(action)
            
            agent_input = self._update_input(
                agent_input, original_response, next_obs, need_update_history, original_prompt, turn_id, summary_content, consecutive_search_cnt
            )
            
            turn_elapsed = time.time() - turn_start_time
            self._log(f"Turn {turn_id} completed in {turn_elapsed:.2f}s")
        
        result = {"website": self.website, "summary": "No relevant information found."}
        elapsed_time = time.time() - start_time
        self._log(f"Retrieval completed in {elapsed_time:.2f}s")
        self._log(f"Final result:\n{result}")
        self._log_session_end()
        return result
