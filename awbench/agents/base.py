"""Shared behaviour for the LLM agents (UserAgent / ContentAgent).

These helpers used to be copy-pasted across both agents. Subclasses must define
the class attribute ``ACTIONS`` (the list of valid action tag names).
"""
import traceback

from awbench.utils.check_error import is_fatal_error


class BaseAgent:
    # Valid action tag names; overridden by each subclass.
    ACTIONS: list[str] = []

    def _postprocess_response(self, response):
        """Post-process the model response to extract the final valid action.

        Args:
            response: response text
        Returns:
            processed response (formatted action); None if the format is invalid.

        Rules (normal case, no <summary>):
        1. An action is considered valid if it appears at least once
        2. Multiple valid actions are allowed in one response
        3. The final action is the action whose last <action> tag appears last
        4. The content of the final action is taken from the last matched
           <action>...</action> pair
        """
        if response is None:
            return None

        if "</think>" in response:
            response = response.rsplit("</think>", 1)[-1]

        # Count occurrences of each action tag
        tag_counts = {}
        for action in self.ACTIONS:
            start_tag = f'<{action}>'
            end_tag = f'</{action}>'
            tag_counts[action] = {
                'start': response.count(start_tag),
                'end': response.count(end_tag)
            }

        summary_content = None
        if tag_counts.get('summary', {}).get('start', 0) > 0:
            # <summary> must appear exactly once
            if tag_counts['summary']['start'] != 1 or tag_counts['summary']['end'] != 1:
                summary_content = None

            # <summary> must wrap the entire response
            start_idx = response.rfind('<summary>')
            end_idx = response.rfind('</summary>')

            if start_idx != 0 or end_idx != len(response) - len('</summary>'):
                summary_content = None

            # Extract summary content (summary may contain other tags)
            content = response[start_idx + len('<summary>'):end_idx].strip()
            summary_content = f'<summary>{content}</summary>'

        if summary_content is not None:
            return summary_content

        valid_actions = []

        # An action is valid if appears at least once
        for action in self.ACTIONS:
            start_count = tag_counts[action]['start']
            end_count = tag_counts[action]['end']

            if start_count > 0 and end_count > 0:
                valid_actions.append(action)

        # At least one valid action must exist
        if not valid_actions:
            return None

        # Select the final action: the last complete <action>...</action> pair
        # that appears latest in the response.
        last_action = None
        last_end_pos = -1
        last_content = None

        for action in valid_actions:
            start_tag = f'<{action}>'
            end_tag = f'</{action}>'

            start_pos = response.rfind(start_tag)
            end_pos = response.rfind(end_tag)

            if start_pos < end_pos:
                content_start = start_pos + len(start_tag)
                content_end = end_pos
                content = response[content_start:content_end]

                full_end_pos = end_pos + len(end_tag)

                if full_end_pos > last_end_pos:
                    last_end_pos = full_end_pos
                    last_action = action
                    last_content = content

        # If no complete tag pair was found for any action, return None
        if last_action is None:
            return None

        return f'<{last_action}>{last_content}</{last_action}>'

    def _parse_action(self, action):
        """Parse the action to get the action type and content.

        Args:
            action: action, format ensured by postprocess_response
        Returns:
            (action_type, content)
        """
        if action is None:
            raise ValueError("Invalid action: None")

        # Find the first '<' and '>' to extract action_type
        start_tag_open = action.find('<')
        start_tag_close = action.find('>', start_tag_open)
        if start_tag_open == -1 or start_tag_close == -1:
            raise ValueError(f"Invalid action format: {action}")

        action_type = action[start_tag_open + 1:start_tag_close]

        # Find the last '</' and '>' to locate the closing tag
        end_tag_open = action.rfind('</')
        end_tag_close = action.rfind('>', end_tag_open)
        if end_tag_open == -1 or end_tag_close == -1:
            raise ValueError(f"Invalid action format: {action}")

        content = action[start_tag_close + 1:end_tag_open].strip()

        return action_type, content

    def _classify_llm_error(self, e, check_spending_limit=True, clean_http=True):
        """Classify an exception raised by an LLM call.

        Re-raises fatal / context-length / (optionally) rate-limit errors so the
        caller stops retrying. For retryable errors it prints diagnostics and
        returns a cleaned error string.
        """
        if is_fatal_error(e):
            print(f"FATAL ERROR detected: {e}")
            print(traceback.format_exc())
            print("Stopping task due to fatal error.")
            raise e

        error_str = str(e)
        if "context" in error_str:
            raise ValueError(f"Context length error: {e}")
        if check_spending_limit and \
                "You have exceeded your monthly spending limit for Inference Providers." in error_str:
            raise ValueError(f"Rate limit error: {e}")

        if clean_http:
            if "504" in error_str or "Gateway Timeout" in error_str:
                error_str = "504 Gateway Timeout - Server timeout"
            elif "500" in error_str:
                error_str = "500 Internal Server Error"
            print(f"Error: {error_str}")
            print(traceback.format_exc().split('<html class="" lang="en">')[0])
        else:
            print(f"Error: {e}")
            print(traceback.format_exc())

        return error_str
