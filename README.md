# trigger-cli

A command-line tool for [Trigger.dev](https://trigger.dev) - list, search, and run tasks from your terminal.

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/trigger-cli.git ~/trigger-cli

# Add alias to your shell profile (.bashrc, .zshrc, etc.)
alias trigger='python3 ~/trigger-cli/trigger.py'
```

### Requirements

- Python 3.6+
- `requests` library (`pip install requests`)
- Optional: `python-dotenv` for .env file support (`pip install python-dotenv`)

## Setup

Set your Trigger.dev credentials:

```bash
export TRIGGER_SECRET_KEY="tr_dev_..."  # or tr_prod_...
export TRIGGER_PROJECT_ID="your-project-id"  # optional, for dashboard URLs
```

Or create a `.env` / `.env.local` file in your project directory.

## Usage

```
trigger                            List tasks (numbered)
trigger list                       Same as above
trigger list <search>              Search tasks by name
trigger list --local               Scan ./tasks folder for all task definitions
trigger schedules                  List scheduled tasks (numbered)
trigger run <task_id>              Run a task (asks for confirmation)
trigger run <task_id> -y           Run without confirmation
trigger run <task_id> -p <json>    Run with JSON payload
trigger run <task_id> --open       Open run URL after trigger
trigger <number>                   Run task by number from last list
trigger -h, --help                 Show this help
```

### Examples

```bash
# List tasks from recent runs
$ trigger
Tasks:
  1. process-campaigns ✓
  2. send-notifications ⏳

# Search tasks
$ trigger list email
Tasks matching 'email':
  1. send-email-batch ✓

# List all tasks from source code
$ trigger list --local
Tasks (local):
  1. cleanup-cron
  2. process-campaigns
  3. send-email-batch
  ...

# Run a task by number
$ trigger 1
Trigger 'process-campaigns'? [y/N] y
✓ Triggered process-campaigns
   https://cloud.trigger.dev/projects/v3/.../runs/...

# Run with payload
$ trigger run my-task -p '{"userId": "123"}'
```

## License

MIT
