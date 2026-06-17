"""
UserAgent: the coordinator (user-side) agent.

Plans over multiple turns, issues <search> actions (dispatched to content agents
or retrieval tools depending on `method`), and synthesizes the final answer.
"""
import os
import re
import json
import time
import random
import traceback
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from awbench.websites import query_websites
from awbench.doc_retrieval import query_docs
from awbench.config import CONCURRENT_NUM
from awbench.prompts import format_reminder_prompt, summary_reminder_prompt
from awbench.agents.base import BaseAgent
from awbench.agents.llm_client import get_llm_client, call_llm
from awbench.utils.token_calculator import tokenize
from awbench.utils.check_error import is_fatal_error

# Action vocabulary the user agent may emit.
ACTIONS = ['search', 'answer', 'plan', 'scripts', 'summary']
MAX_CONTEXT_LENGTH = 8000


class UserAgent(BaseAgent):
    ACTIONS = ACTIONS

    def __init__(
        self,
        config,
        log_dir: str,
        answer_dir: str,
        task_type: str = "qa",
        verbose: bool = False,
        api_type: str = "gemini",
        model_id: str = None,
        url: str = None,
        method: str = 'multi_agent',
        content_agent_max_turns: int = 15,
        docs_per_site: int = 5,
    ):
        self.task_type = task_type
        self.is_deep_research = task_type == "deep_research"
        self.is_web_search = task_type == "web_search"
        self.is_web_recommendation = task_type == "web_recommendation"

        # Initialize client and model using unified LLM client
        self.api_type = api_type
        self.client, self.model_name = get_llm_client(api_type, model_id, url)
        self.url = url
        self.method = method
        self.consecutive_search_cnt = {} # Number of consecutive search actions performed for each sample
        self.search_cnt = {} # Number of total search actions performed for each sample
        self.script_cnt = {} # Number of total script actions performed for each sample
        self.summary_cnt = {} # Number of total summary actions performed for each sample
        self.context_cnt = {} # Number of total context length in each turn for each sample
        self.turn_id = {} # Turn ID for each question
        self.summary_history = {} # History of summary actions performed for each sample
        self.need_format_reminder = {} # Whether a format reminder prompt is needed for each sample
        self.config = config
        self.verbose = verbose
        self.log_dir = log_dir
        self.answer_dir = answer_dir
        self.questions = {}
        self.content_agent_max_turns = content_agent_max_turns
        self.docs_per_site = docs_per_site
        print(f"#######\nInit UserAgent with API type: {self.api_type}, model: {self.model_name}, mode: {self.task_type}, method: {self.method}\n#######")


    def run_llm_loop(self, prompt, question_id):
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        trajectory_log = f"{self.log_dir}/user_agent_trajectory_{question_id}.md"
        trajectory_jsonl_log = f"{self.log_dir}/user_agent_trajectory_{question_id}.jsonl"
        search_log = f"{self.log_dir}/search_{question_id}.log"

        # Clear logs
        with open(trajectory_log, 'w', encoding='utf-8') as f:
            f.write('')
        if self.verbose:
            with open(trajectory_jsonl_log, 'w', encoding='utf-8') as f:
                f.write('')

        print(f"Running question {question_id}")

        done = False
        agent_input = prompt
        self.consecutive_search_cnt[question_id] = 0
        self.search_cnt[question_id] = 0
        self.script_cnt[question_id] = 0
        self.summary_cnt[question_id] = 0
        self.context_cnt[question_id] = []
        self.turn_id[question_id] = 0
        self.summary_history[question_id] = ''
        self.need_format_reminder[question_id] = False
        try:
            for step in range(self.config["max_turns"]):
                self.turn_id[question_id] += 1
                print(f"=====turn {self.turn_id[question_id]}======")
                

                if self.api_type == "gemini":
                    response, action = self._query_gemini(agent_input, question_id, trajectory_log)
                elif self.api_type in ("gpt", "hf", "local"):
                    response, action = self._query_gpt(agent_input, question_id)
                else:
                    raise ValueError(f"Unsupported API type: {self.api_type}")
                # execute actions (search or answer) and get observations
                done, need_update_history, next_obs = self._execute_response(
                    action, self.config["num_docs"], question_id, search_log
                )
                self._record_trajectory(agent_input, response, next_obs, trajectory_log, trajectory_jsonl_log, question_id)

                if done:
                    print("=====final response======")
                    break
                agent_input = self._update_input(
                    agent_input, response, next_obs, question_id, need_update_history, prompt
                )
            
            answer = self._compose_final_output(action)
            self._log_result(answer=answer, question_id=question_id)
                
            print(f"Question {question_id} result saved to {self.answer_dir}/result_{question_id}.json\n")
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            # If it's a fatal error, re-raise to stop the entire task
            if is_fatal_error(e):
                print(f"FATAL ERROR detected: {e}")
                print(traceback.format_exc())
                print("Stopping entire task due to fatal error.")
                raise

    def run_llm_loop_parallel(self, prompts, questions, question_ids):
        print(f"Running {len(prompts)} questions in parallel with {CONCURRENT_NUM} workers")

        for i, question_id in enumerate(question_ids):
            question = questions[i]
            self.questions[question_id] = question
            
        with ThreadPoolExecutor(max_workers=CONCURRENT_NUM) as executor:
            futures = [executor.submit(self.run_llm_loop, prompt, question_id) 
                for prompt, question_id in zip(prompts, question_ids)]
            concurrent.futures.wait(futures)

    def _query_gpt(self, prompt, question_id):
        """Query GPT/OpenAI-compatible API with action format check.
        Args:
            prompt: prompt
        Returns:
            response: response with correct format and thought process
        """
        max_try_times = 5
        for attempt in range(max_try_times):
            try:
                response, thought = call_llm(
                    self.api_type,
                    self.client,
                    self.model_name,
                    prompt,
                )
                break

            except Exception as e:
                self._classify_llm_error(e)

                if attempt == max_try_times - 1:
                    raise ValueError(f"Failed to get response after {max_try_times} tries: {e}")
                else:
                    time.sleep(random.randint(1, 3))

        action = self._postprocess_response(response) # if format is not correct, action is None

        if thought is not None and len(thought) > 0:
            original_response = f'<think>{thought}</think>\n{response}'
        else:
            original_response = response if response is not None else ''
        
        context_length = tokenize(prompt) + tokenize(original_response)
        self.context_cnt[question_id].append(context_length)

        return original_response, action
    
    def _query_gemini(self, prompt, question_id, trajectory_log):
        """Query Gemini with action format check. Only return the response with correct format.
        Args:
            prompt: prompt
        Returns:
            response: response with correct format and thought process
        """
        max_try_times = 5
        response = None  
        thought = None
        action = None
        
        for attempt in range(max_try_times):
            try:
                response, thought = call_llm(
                    self.api_type,
                    self.client,
                    self.model_name,
                    prompt,
                )

                if response is not None:
                    action = self._postprocess_response(response)
                    if action is not None: # if format is correct, break
                        break

            except Exception as e:
                # Gemini keeps its own diagnostics + 503 backoff below, so skip
                # the spending-limit / HTTP-cleaning branches of the shared helper.
                self._classify_llm_error(e, check_spending_limit=False, clean_http=False)

                if attempt == max_try_times - 1:
                    raise ValueError(f"Failed to get response after {max_try_times} tries: {e}")
                else:
                    # Check if it's a 503 error (server overloaded)
                    from google.genai import errors as genai_errors
                    is_503_error = (
                        (isinstance(e, genai_errors.ServerError) and
                         hasattr(e, 'status_code') and e.status_code == 503) or
                        "503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower()
                    )

                    if is_503_error:
                        # Exponential backoff for 503 errors: 2^retry_count seconds + random jitter
                        base_delay = 2 ** (attempt + 1)  # Start from 2 seconds, then 4, 8, 16...
                        jitter = random.uniform(0.5, 1.5)  # Random jitter between 0.5-1.5 seconds
                        sleep_time = min(base_delay + jitter, 60)  # Cap at 60 seconds
                        print(f"503 error detected, waiting {sleep_time:.2f} seconds before retry (attempt {attempt + 1}/{max_try_times})")
                        time.sleep(sleep_time)
                    else:
                        # Random sleep 1-3 seconds for other errors
                        time.sleep(random.randint(1, 3))
           
        
        if thought is not None and len(thought) > 0:
            original_response = f'<think>{thought}</think>\n{response}'
        else:
            original_response = response if response is not None else ''

        context_length = tokenize(prompt) + tokenize(original_response)
        self.context_cnt[question_id].append(context_length)

        return original_response, action

    def _execute_response(self, action, num_docs, question_id, search_log, do_search=True):
        """
        Args:
            action: action to be executed, None if format is not correct
            num_docs: number of docs to retrieve
            search_log: file to log search output
            do_search: whether to perform search
        Returns:
            done: whether the task is done
            need_update_history: whether need to update the history to agent summary
            next_obs: next observation
        """

        if action is None:
            self.need_format_reminder[question_id] = True
            next_obs = 'An invalid action, cannot be executed.'
            return False, False, next_obs

        action, content = self._parse_action(action)
        if action not in ACTIONS:
            raise ValueError(f"Invalid action: {action}")

        next_obs = ''
        done = False
        need_update_history = False

        search_query = content if action == 'search' else ''
        
        if do_search and search_query != '':    
            search_results = self._search(search_query, num_docs, search_log, question_id)
        else:
            search_results = ''

        if action == 'search':
            self.search_cnt[question_id] += 1
            self.consecutive_search_cnt[question_id] += 1
            observation = f'<information>{search_results}</information>'
            next_obs += observation
        
        if action == "answer":
            done = True
            next_obs += 'Answer generated, the process is done.'
        if action == 'plan':
            self.consecutive_search_cnt[question_id] = 0
        if action == 'scripts':
            self.consecutive_search_cnt[question_id] = 0
            self.script_cnt[question_id] += 1
        if action == 'summary':
            next_obs += 'You performed a summary action in this turn. The content of this action is ignored since your history turns information has been updated according to it.\n'
            self.consecutive_search_cnt[question_id] = 0
            self.summary_cnt[question_id] += 1
            self.summary_history[question_id] = content
            need_update_history = True

        return done, need_update_history, next_obs

    def _record_trajectory(self, agent_input, response, next_obs, trajectory_log, trajectory_jsonl_log, question_id):
        """Record the trajectory of the agent.
        Args:
            agent_input: input
            response: response
            trajectory_log: path to trajectory log file
        """
        with open(trajectory_log, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"## Turn {self.turn_id[question_id]} {timestamp}\n\n")

            input_length = tokenize(agent_input)
            response_length = tokenize(response)
            
            # Create patterns for all action types and truncate long contents
            for action in ['search', 'answer', 'plan', 'scripts', 'information']:
                pattern = f'<{action}>(.*?)</{action}>'
                
                def truncate_action_content(match):
                    """Truncate action content if it's too long"""
                    full_content = match.group(1)  # Content between action tags
                    if len(full_content) > 100:
                        truncated_content = full_content[:100] + '...'
                        return f'<{action}>{truncated_content}</{action}>'
                    else:
                        return match.group(0)  # Return original if short enough
                
                input_short = re.sub(pattern, truncate_action_content, agent_input, flags=re.DOTALL)
            
            f.write(f"### Input:\n**length={input_length}**\n{input_short}\n\n")
            f.write(f"### Response:\n**length={response_length}**\n{response}\n\n--------------------------------\n\n")

        if self.verbose:
            with open(trajectory_jsonl_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "input": agent_input,
                    "response": response,
                    "next_obs": next_obs,
                    "context_length": input_length + response_length
                }) + '\n')

    def _update_input(self, agent_input, cur_response, next_obs, question_id, need_update_history, original_prompt):
        """Update the input with the history.
        Args:
            agent_input: input
            cur_response: current full response
            next_obs: next observation
            need_update_history: whether update the history to agent summary
            original_prompt: original prompt for the question
        Returns:
            updated input
        """
        if self.need_format_reminder[question_id]: # there is no valid action in this turn, need format reminder prompt
            context = f"[Turn {self.turn_id[question_id]}]:\n{cur_response}\n\n"
            context += format_reminder_prompt
            new_input = agent_input + context
            self.need_format_reminder[question_id] = False
        else:
            if need_update_history:
                context = f"[Turn 0 - Turn {self.turn_id[question_id] - 1}]:\n{self.summary_history[question_id]}\n\n"
                context += f"[Turn {self.turn_id[question_id]}]:\n{next_obs}\n\n"
                new_input = original_prompt + context
            else:
                context = f"[Turn {self.turn_id[question_id]}]:\n{cur_response}\n{next_obs}\n\n"
                new_input = agent_input + context

        # add reminder for search and final report
        if self.turn_id[question_id] + 1 == self.config["final_answer_turn"]:
            new_input += f'\nNote: You have performed {self.turn_id[question_id]} turns. Please output the final report/answer.'
        else:
            if self.turn_id[question_id] > self.config["final_answer_reminder_turn"]:
                new_input += f'\nNote: You have performed {self.turn_id[question_id]} turns. Please consider output the final report. If you still want to search, make sure you check history search results and DO NOT perform duplicate search.'
            if self.consecutive_search_cnt[question_id] > self.config["search_reminder_turn"]:
                new_input += f'\nNote: You have performed {self.consecutive_search_cnt[question_id]} search actions. Please consider update your report scripts or output the final report. If you still want to search, make sure you check history search results and DO NOT perform duplicate search.'
            
            # add summary reminder prompt if context is too long
            input_length = tokenize(new_input)
            if input_length > MAX_CONTEXT_LENGTH:
                new_input += summary_reminder_prompt

        return new_input

    def _compose_final_output(self, response):
        if response is not None and '<answer>' in response and '</answer>' in response:
            answer_content = response.split('<answer>')[1].split('</answer>')[0].strip()
            if self.is_web_search or self.is_web_recommendation:
                # For web_search / web_recommendation, parse JSON array of document IDs
                try:
                    # Try to parse as JSON array
                    doc_ids = json.loads(answer_content)
                    if isinstance(doc_ids, list):
                        return json.dumps(doc_ids)  # Return as JSON string
                    else:
                        return answer_content
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse JSON in answer content: {answer_content}")
                    # If not valid JSON, try to extract document IDs from text
                    # Look for patterns like "doc_id=<id>" or just document IDs
                    # Try to find document IDs in various formats
                    doc_id_pattern = r'doc_id[=:]?\s*([^\s,)\]]+)'
                    doc_ids = re.findall(doc_id_pattern, answer_content)
                    if doc_ids:
                        return json.dumps(doc_ids)
                    # If no pattern found, return as is
                    return answer_content
            else:
                return answer_content
        else:
            if self.is_web_search or self.is_web_recommendation:
                return '[]'  # Return empty list for document retrieval / web_recommendation
            else:
                return 'did not find answer'

    def _log_result(self, answer, question_id):
        answer_file = f"{self.answer_dir}/result_{question_id}.json"
        with open(answer_file, 'w', encoding='utf-8') as f:
            result = {
                    "model": self.model_name,
                    "question": self.questions[question_id],
                    "answer": answer,
                    "turns": self.turn_id[question_id],
                    "search count": self.search_cnt[question_id],
                    "script count": self.script_cnt[question_id],
                    "summary count": self.summary_cnt[question_id],
                    "context lengths": self.context_cnt[question_id]
                }
            json.dump(result, f, indent=4)

    def _search(self, query, num_docs, search_log, question_id):
        # Extract log_dir from search_log path for agent logging
        log_dir = os.path.dirname(search_log) if search_log else None
        
        # Prepare LLM config for content agents (same as user agent)
        llm_config = {
            "api_type": self.api_type,
            "model_id": self.model_name,
            "url": self.url,
        }
        try:
            # classical: Standard Document Retrieval, Without MCP environment; uses embedding similarity between queries and documents.
            # tool_prompt: Single User Agent (Prompt-based), With MCP environment; the user agent selects websites for queries using a prompt-based method.
            # tool_embed: Single User Agent (Embedding-based), With MCP environment; uses embedding similarity between queries and websites (website embeddings are computed as the average embedding of 100 web documents).
            # multi_agent: Single User Agent + Multiple Content Agents
            if self.method == 'tool_prompt':
                query = json.loads(query)
                documents = query_websites(query, log_dir=log_dir, question_id=question_id, content_agent_max_turns=self.content_agent_max_turns, docs_per_site=self.docs_per_site, llm_config=llm_config)
            elif self.method == 'tool_embed':
                documents = query_websites(query, log_dir=log_dir, question_id=question_id, content_agent_max_turns=self.content_agent_max_turns, docs_per_site=self.docs_per_site, llm_config=llm_config)
            elif self.method == 'classical':
                documents = query_docs(query, num_docs=num_docs)
            elif self.method == 'multi_agent':
                query = json.loads(query)
                documents = query_websites(query, agent_mode=True, log_dir=log_dir, question_id=question_id, content_agent_max_turns=self.content_agent_max_turns, docs_per_site=self.docs_per_site, llm_config=llm_config)
            else:
                raise ValueError(f"Invalid method: {self.method}")
            info_retrieved = json.dumps(documents, indent=4)

            return info_retrieved
        except json.JSONDecodeError as e:
            print(f"Error in _search: {e} for {query}")
            print(traceback.format_exc())
            return f"Error in _search: {e} for \"{query}\""
