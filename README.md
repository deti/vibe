# vibe

Vibe coding supervisor without batteries

A lightweight coding supervisor that integrates with Claude Code to execute prompts and automatically run project checks with intelligent retry logic.

## Features

* **Claude Code Integration** - Invoke Claude Code headless with prompts from files
* **Automated Check Execution** - Run configured checks after Claude operations
* **Intelligent Retry Logic** - Automatically retry failed checks by calling Claude to fix issues
* **Flexible Configuration** - Environment-based settings and project-specific YAML configuration
* **JSON Output Parsing** - Structured output from Claude operations with session tracking

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Prerequisites

* Python >= 3.14
* [uv](https://github.com/astral-sh/uv) package manager
* [Claude Code](https://claude.ai/code) CLI installed and configured

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/deti/vibe.git
   cd vibe
   ```

2. Initialize the project:
   ```bash
   make init
   ```
   Or manually:
   ```bash
   uv venv
   uv sync
   ```

3. (Optional) Create a `.env` file from the template:
   ```bash
   cp env.template .env
   ```

## Usage

### Main Command

Invoke Claude Code with a prompt from a file:

```bash
vibe <prompt_file>
```

The command will:
1. Load project configuration (if `.vibe/vibe.yaml` exists)
2. Read the prompt from the specified file
3. Invoke Claude Code with the prompt
4. Display the parsed JSON output (including session ID and result)
5. Run configured checks (if any)
6. Automatically retry failed checks by calling Claude to fix issues

## Configuration

Vibe supports two types of configuration:

1. **Application Settings** - Global settings via environment variables or `.env` file
2. **Project Configuration** - Project-specific settings via `.vibe/vibe.yaml`

### Application Settings

Application settings control the behavior of the vibe application itself. These are loaded from environment variables or a `.env` file in the project root.

#### Configuration Precedence

Settings are loaded in the following order (later sources override earlier ones):

1. Default values (defined in code)
2. `.env` file (if present in project root)
3. Environment variables

#### Viewing Current Settings

To see the current settings (after applying environment variables and `.env` file):

```bash
show-settings
```

This outputs JSON with all current settings.

### Project Configuration

Project configuration defines checks to run after Claude operations. This is stored in `.vibe/vibe.yaml` in your project root.

#### Configuration Structure

```yaml
checks:
  steps:
    - name: "Check Name"
      command: "command to execute"
    - name: "Another Check"
      command: "another command"
  max_retries: 10
```

#### Configuration Fields

**`checks`** (optional)
- Configuration for automated checks

  **`steps`** (list, default: `[]`)
  - List of check steps to execute
  
    **`name`** (string, required)
    - Human-readable name for the check step
    
    **`command`** (string, required)
    - Shell command to execute for this check

  **`max_retries`** (integer, default: `10`)
  - Maximum number of retry attempts when checks fail
  - When checks fail, Claude is automatically called with a fix prompt
  - Retries continue until all checks pass or `max_retries` is reached

#### Example Configuration

Create `.vibe/vibe.yaml` in your project root:

```yaml
checks:
  steps:
    - name: "Run Tests"
      command: "pytest tests/"
    - name: "Lint Code"
      command: "ruff check src/"
    - name: "Type Check"
      command: "mypy src/"
  max_retries: 5
```

#### How Checks Work

1. After Claude executes a prompt, configured checks are run sequentially
2. If any check fails, Claude is automatically invoked with a fix prompt containing:
   - The failed check commands
   - Error outputs from failed checks
3. Claude attempts to fix the issues
4. All checks are re-run
5. This process repeats until:
   - All checks pass, or
   - `max_retries` is reached

#### Running Without Project Configuration

If `.vibe/vibe.yaml` doesn't exist, vibe will:
- Skip check execution
- Still execute Claude with your prompt
- Display a message indicating no project configuration was found

## Development

### Running Tests

```bash
make test
```

Or with coverage:

```bash
make test-cov
```

### Linting

```bash
make lint
```

This runs `ruff check` and `ruff format` on the codebase.

### Available Make Commands

```bash
make help
```

Common commands:
- `make init` - Initialize project dependencies
- `make sync` - Install/update dependencies (with dev dependencies)
- `make sync-prod` - Install without dev dependencies
- `make test` - Run tests
- `make lint` - Run linting and formatting
- `make clean` - Clean up generated files

## Project Structure

```
vibe/
├── src/vibe/
│   ├── cli/           # CLI commands
│   ├── providers/     # AI provider integrations (Claude)
│   ├── checks.py      # Check execution and retry logic
│   ├── project_config.py  # Project configuration loading
│   └── settings.py    # Application settings
├── tests/             # Test suite
├── .vibe/             # Project configuration directory (created per project)
│   └── vibe.yaml      # Project-specific configuration
├── .env               # Application settings (optional)
└── env.template       # Template for .env file
```
