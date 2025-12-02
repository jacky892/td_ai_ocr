## Learning from Mistakes

1.  **jsondiff Issue:** I incorrectly assumed the `jsondiff` library had a `dump` function. This led to a persistent `ImportError` that I misdiagnosed as a user environment issue, causing significant user frustration. The correct solution was to find that `dump` does not exist and manually convert the `diff` output's `Symbol` keys to strings before passing the result to the standard `json.dump`. **Lesson:** Verify third-party library APIs instead of assuming. Trust the user's traceback when it is clear and unambiguous.

2.  **Debugging Output (`ollama_cli` timeout):** When the user reported a `subprocess` timeout that they could not reproduce manually, I again wrongly assumed the issue was with the user's setup. I failed to add crucial debugging output to the exception handler. The script should have been modified to print the captured `stdout` and `stderr` from the timed-out process. This would have immediately shown what the script was seeing. **Lesson:** Be proactive in adding comprehensive debug logging to prove what the script is doing, especially for I/O and subprocess operations. Do not dismiss user reports that conflict with my assumptions.

3.  **Syntax Validation:** I have repeatedly introduced `SyntaxError` into the script through malformed `print` statements and other basic mistakes. This is a critical failure. **Lesson:** I must internally validate the syntax of any code I generate before delivering it. A non-runnable script is a complete failure.

4.  **Use User Test Cases:** The user has consistently provided the exact command they are using to test. I failed to properly incorporate this into my own validation loop. **Lesson:** I must use the user's provided commands and context to test and verify my changes to ensure they solve the specific problem the user is facing.

5.  **Robust Parsing of CLI Output:** The `ollama run` command produces a complex stream containing conversational text and ANSI escape codes (`\x1b[...]`) for cursor animation. My initial parsing logic, which simply searched for the first `{` character, was brittle and failed completely. **Lesson:** Raw CLI output cannot be trusted. It must be sanitized. I must account for and strip non-data characters like ANSI codes, and use more robust logic (like reverse searching for the *last* JSON object) to reliably extract data.

6, **always print out the ollama response (http or cli) complete for parsing, as model output can vary, don't assume anthing, for example sometimes the answer can be in the thinking tokens.
