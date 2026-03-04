from flask import Flask, render_template, request
import io, sys

import batch_runner
import summary as summary_module

app = Flask(__name__)


def _capture(func, *args, **kwargs):
    """Helper to call a function and capture its stdout output as a string."""
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        result = func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout
    return buffer.getvalue(), result


@app.route("/", methods=["GET", "POST"])
def index():
    log = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "demo":
            log, _ = _capture(batch_runner.run_demo)
        elif action == "onboarding":
            log, _ = _capture(batch_runner.run_onboarding)
        elif action == "summary":
            summ = summary_module.generate_summary()
            log, _ = _capture(summary_module.print_summary_table, summ)
    else:
        # on GET show current summary by default
        summ = summary_module.generate_summary()
        log, _ = _capture(summary_module.print_summary_table, summ)
    return render_template("index.html", log=log)


if __name__ == "__main__":
    app.run(debug=True)
