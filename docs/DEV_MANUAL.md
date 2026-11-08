# Developer Manual for `scripts/`

This section details all utilities in `scripts/`.

## scripts/ast_complexity.py
### Programmatic APIs
Functions: `compute_complexity(filepath, source_code)`, `analyze_files(filepaths)`
Classes: `FunctionComplexity`, `ComplexityVisitor`

### CLI Flags
```text
usage: ast_complexity.py [-h] [--max-complexity MAX_COMPLEXITY]
                         [--sort-by-complexity]
                         files [files ...]

AST Cyclomatic Complexity

positional arguments:
  files                 Files to analyze

options:
  -h, --help            show this help message and exit
  --max-complexity MAX_COMPLEXITY
                        Max complexity
  --sort-by-complexity  Sort results
```

## scripts/benchmark_runner.py
### Programmatic APIs
Functions: `run_iteration(command)`, `calculate_metrics(times, memories)`, `output_results(metrics, csv_path)`

### CLI Flags
```text
usage: benchmark_runner.py [-h] [-n ITERATIONS] [--csv CSV] ...

Benchmark runner

positional arguments:
  command

options:
  -h, --help            show this help message and exit
  -n ITERATIONS, --iterations ITERATIONS
  --csv CSV             Output CSV path
```

## scripts/boost_types.py
### Programmatic APIs
Functions: `infer_literal_type(node)`, `collect_return_types(fn_node)`, `infer_return_annotation(fn_node, fallback_any)`, `find_signature_bounds(lines, start_lineno)`, `boost_function_signature(fn_node, lines, fallback_any)`, `boost_file(file_path, fix, fallback_any)`
Classes: `InferredFunction`

### CLI Flags
```text
usage: boost_types.py [-h] [--fix] [--fallback-any] [--check] [target]

Type Annotation Booster (Deterministic Safe AST Type Engine)

positional arguments:
  target          Target file or directory to boost (default: current
                  directory)

options:
  -h, --help      show this help message and exit
  --fix           Apply boosted type annotations in-place (verifies AST before
                  saving)
  --fallback-any  Annotate uninferrable parameters with Any (and ensure from
                  typing import Any)
  --check         Exit with code 1 if unannotated functions can be boosted
```

## scripts/branch_auditor.py
### Programmatic APIs
Functions: `run_git_command(git_args)`, `get_default_branch()`, `get_merged_branches(default_branch)`, `get_stale_unmerged_branches(default_branch)`, `prune_merged_branches(branches, is_dry_run)`

### CLI Flags
```text
usage: branch_auditor.py [-h] [--dry-run] [--prune-merged]

Audit git branches.

options:
  -h, --help      show this help message and exit
  --dry-run       Print actions without modifying state.
  --prune-merged  Delete merged local branches.
```

## scripts/changelog_generator.py
### Programmatic APIs
Functions: `parse_commit_message(hash_str, author, message)`, `get_git_commits(start_rev, end_rev)`, `categorize_commits(commits_list)`, `generate_markdown(version_name, publish_date, grouped_commits)`
Classes: `Commit`

### CLI Flags
```text
usage: changelog_generator.py [-h] [--start START] [--end END] --version
                              VERSION

Generate changelog

options:
  -h, --help         show this help message and exit
  --start START      Start revision
  --end END          End revision
  --version VERSION  Version name
```

## scripts/check_dependencies.py
### Programmatic APIs
Functions: `get_stdlib_modules()`, `find_local_modules(project_root)`, `extract_imports_from_file(file_path)`, `clean_package_name(raw_name)`, `parse_requirements_file(req_file)`, `parse_pyproject_toml(pyproject_file)`, `get_declared_dependencies(project_root)`, `get_installed_distributions()`, `scan_dependencies(target_path, project_root)`

### CLI Flags
```text
usage: check_dependencies.py [-h] [--project-root PROJECT_ROOT] [--strict]
                             [--json]
                             [target]

Hallucinated Dependency Scanner (Identifies fake/missing AI package imports)

positional arguments:
  target                Target file or directory to scan (default: current
                        directory)

options:
  -h, --help            show this help message and exit
  --project-root PROJECT_ROOT
                        Project root directory containing requirements.txt or
                        pyproject.toml
  --strict              Fail (exit 1) on both hallucinated and undeclared
                        dependencies
  --json                Output results in JSON format
```

## scripts/check_variable_names.py
### Programmatic APIs
Functions: `is_descriptive_name(name, context)`, `audit_file(path)`, `scan_directory(target)`
Classes: `VariableAuditor`

### CLI Flags
```text
usage: check_variable_names.py [-h] [target]

Audit codebase for descriptive variable and parameter names.

positional arguments:
  target      Target file or directory

options:
  -h, --help  show this help message and exit
```

## scripts/claudemd_linter.py
### Programmatic APIs
Functions: `noqa_codes(line)`, `suppressed(line, code)`, `scan_text_line(...)`, `scan_markdown_headings(...)`, `scan_comment_blocks(...)`, `extract_function_bodies(source)`, `detect_duplicate_code(...)`, `detect_unused_code(files, violations)`, `detect_module_graph_issues(...)`, `scan_python_ast(...)`, `scan_dialog_label_selectability(...)`, `scan_missing_tooltips(...)`, `scan_os_specific_code(...)`, `scan_single_file(path_str)`, `scan_file(path, violations)`, `load_cache()`, `save_cache(cache)`, `get_file_hash(path)`, `is_scannable_file(fpath)`, `collect_git_diff_files(...)`, `collect_files(target)`, `audit_suppressions(target)`, `run_standard_linter(target_dir)`, `is_git_repository(cwd)`, `calc_report_path(root, custom_path)`, `parse_cli_args(raw_args)`

### CLI Flags
```text
usage: claudemd_linter.py <target> [--level LEVEL] [--skip CODES] [--only CODES] [--noqa] [--diff] [--staged] [--full] [--no-cache] [--no-parallel] [--no-ruff]
```

## scripts/clean_encoding.py
### Programmatic APIs
Functions: `clean_content(content, degrees_to_word)`, `process_file(path, dry_run, degrees_to_word)`, `scan_directory(target)`

### CLI Flags
```text
usage: clean_encoding.py [-h] [--dry-run] [--degrees-to-word] [target]

Scan and clean character encoding corruption (mojibake).

positional arguments:
  target             File or directory to scan (default: current directory)

options:
  -h, --help         show this help message and exit
  --dry-run          Preview fixes without modifying files
  --degrees-to-word  Replace '°' with the word 'degrees'
```

## scripts/configure.py
### Programmatic APIs
Functions: `get_tool_definitions(workspace)`, `calc_linter_command()`, `build_instructions(frontmatter)`, `install_file(dest, content, default_action, dry_run)`, `remove_tool_targets(selected_tools, scope, workspace, dry_run)`, `configure_tools(selected_tools, scope, workspace, action, dry_run)`, `configure_mcp_servers(repo_root, scope, workspace, tools, dry_run, remove)`, `configure_skills(repo_root, scope, workspace, dry_run, remove)`, `interactive_menu()`

### CLI Flags
```text
usage: configure.py [-h] [--tools TOOLS] [--scope {global,workspace,both}]
                    [--workspace WORKSPACE]
                    [--action {ask,overwrite,append,skip}] [--no-mcp]
                    [--no-skills] [--dry-run] [--remove]

Configure Developer's AI development tools across platforms.

options:
  -h, --help            show this help message and exit
  --tools TOOLS         Comma-separated list of tools (claude, cursor, cline,
                        antigravity, codex, windsurf, copilot, aider, all)
  --scope {global,workspace,both}
                        Installation scope: global user profile, workspace
                        project, or both.
  --workspace WORKSPACE
                        Path to workspace root (used when scope is workspace
                        or both).
  --action {ask,overwrite,append,skip}
                        Action when a destination file already exists.
  --no-mcp              Skip automatic configuration of Model Context Protocol
                        (MCP) servers.
  --no-skills           Skip automatic installation of Antigravity skills.
  --dry-run             Preview actions without modifying files.
  --remove              Remove configured rules and MCP servers for selected
                        tools.
```

## scripts/dead_assets.py
### Programmatic APIs
Functions: `find_assets(root_path)`, `extract_asset_names(assets)`, `scan_codebase_for_references(root_path, asset_names)`, `format_size(size_bytes)`, `get_dead_assets(root_path)`

### CLI Flags
```text
usage: dead_assets.py [-h] [path]

Find dead assets in project.

positional arguments:
  path        Project root path

options:
  -h, --help  show this help message and exit
```

## scripts/dir_overview.py
### Programmatic APIs
Functions: `count_lines_and_size(p)`, `render_tree(dir_path, prefix, current_depth, max_depth, allowed_exts, max_files, stats, file_counter)`

### CLI Flags
```text
usage: dir_overview.py [-h] [--depth DEPTH] [--ext EXT] [--stats]
                       [--max-files MAX_FILES]
                       [target]

Token-efficient codebase hierarchy and file size visualizer

positional arguments:
  target                Target directory (default: .)

options:
  -h, --help            show this help message and exit
  --depth DEPTH, -d DEPTH
                        Maximum recursion depth (default: 3)
  --ext EXT             Filter by comma-separated file extensions (e.g.
                        py,js,ts)
  --stats, -s           Display line count and file size in KB
  --max-files MAX_FILES, -m MAX_FILES
                        Maximum files to display (default: 150)
```

## scripts/doctor.py
### Programmatic APIs
Functions: `check_git_tracking(repo_root)`, `check_python_version(repo_root)`, `inspect_mcp_config(mcp_path)`, `check_installed_skills(repo_root, home)`, `get_all_config_paths()`, `inspect_config_file(name, path)`, `heal_config_file(info)`, `clean_stale_reports_and_cache(dry_run)`, `run_diagnostics(auto_heal, clean_cache, repair)`

### CLI Flags
```text
usage: doctor.py [-h] [--heal] [--clean] [--repair]

Run diagnostics and heal stale AI tool paths.

options:
  -h, --help  show this help message and exit
  --heal      Automatically heal stale paths without asking
  --clean     Remove stale lint reports and .lint_cache.json
  --repair    Automated repair to reinstall missing skills
```

## scripts/env_validator.py
### Programmatic APIs
Functions: `parse_line(line)`, `parse_file(filepath)`, `validate_type(val, t_ann)`, `validate_env(env_path, example_path)`

### CLI Flags
```text
usage: env_validator.py [-h] [--env ENV] [--example EXAMPLE]

options:
  -h, --help         show this help message and exit
  --env ENV
  --example EXAMPLE
```

## scripts/fast_search.py
### Programmatic APIs
Functions: `is_binary_file(path)`, `search_in_file(path, pattern, context, max_matches_per_file)`

### CLI Flags
```text
usage: fast_search.py [-h] [--regex] [-i] [-C CONTEXT] [--ext EXT]
                      [--max-results MAX_RESULTS] [--names-only]
                      query [target]

Fast, token-efficient regex & symbol search for codebases

positional arguments:
  query                 Search string (literal by default)
  target                Target directory (default: .)

options:
  -h, --help            show this help message and exit
  --regex               Treat query as regular expression
  -i, --ignore-case     Case-insensitive search
  -C CONTEXT, --context CONTEXT
                        Context lines around match (default: 1)
  --ext EXT             Filter by comma-separated file extensions (e.g.
                        py,ts,md)
  --max-results MAX_RESULTS, -m MAX_RESULTS
                        Maximum total matches to return (default: 30)
  --names-only          Only list matching filenames
```

## scripts/format_tables.py
### Programmatic APIs
Functions: `extract_rows(table_lines)`, `determine_alignment(delimiter_row)`, `format_cell(cell, width, alignment)`, `format_table(lines)`, `process_content(content)`, `process_file(target_file, check_only)`

### CLI Flags
```text
usage: format_tables.py [-h] [--check] [--write] [files ...]

Format markdown tables

positional arguments:
  files

options:
  -h, --help  show this help message and exit
  --check
  --write
```

## scripts/git_summary.py
### Programmatic APIs
Functions: `run_git_command(repo_path, git_args)`, `get_current_branch(repo_path)`, `get_dirty_file_count(repo_path)`, `get_unpushed_commits(repo_path, branch_name)`, `get_last_commit_info(repo_path)`, `discover_git_repos(parent_directory)`, `get_repo_summary(repo_path)`, `print_tabular_summary(summary_list)`

### CLI Flags
```text
usage: git_summary.py [-h] [--json] [directory]

Git repository summary

positional arguments:
  directory   Parent directory

options:
  -h, --help  show this help message and exit
  --json      Output in JSON format
```

## scripts/grep_keywords.py
### Programmatic APIs
Functions: `iter_files(root, exts, skip_dirs)`, `search(files, pattern, context)`

### CLI Flags
```text
usage: grep_keywords.py [-h] [--ext EXT] [--regex] [--ignore-case]
                        [--context CONTEXT] [--skip-dir SKIP_DIR]
                        keyword [path]

Grep for a keyword/regex across files and folders.

positional arguments:
  keyword              Literal keyword or regex pattern to search for
  path                 File or folder to search (default: cwd)

options:
  -h, --help           show this help message and exit
  --ext EXT            Comma-separated extensions to include, e.g. py,md
  --regex              Treat keyword as a regex instead of a literal string
  --ignore-case        Case-insensitive search
  --context CONTEXT    Lines of context to show around each match
  --skip-dir SKIP_DIR  Additional directory name to skip (repeatable)
```

## scripts/grill_user.py
### Programmatic APIs
No public APIs found.

### CLI Flags
```text
usage: grill_user.py [-h] [--async] [topic]

Grill the user relentlessly about a plan, decision, or idea.

positional arguments:
  topic       The topic, plan, decision, or idea to grill the user about.

options:
  -h, --help  show this help message and exit
  --async     Print questions with recommended defaults formatted for a plan
              or PR.
```

## scripts/import_graph.py
### Programmatic APIs
Functions: `get_module_name(file_path, root_path)`, `parse_imports(file_path, root_path)`, `find_python_files(directory)`, `build_dependency_graph(root_path)`, `detect_cycles(graph)`, `output_dot_graph(graph, out_path)`

### CLI Flags
```text
usage: import_graph.py [-h] [--dot DOT] directory

Import Graph

positional arguments:
  directory   Directory to analyze

options:
  -h, --help  show this help message and exit
  --dot DOT   Output DOT graph to path
```

## scripts/install_antigravity_hooks.py
### Programmatic APIs
Functions: `get_hook_paths(workspace)`, `build_hook_config(command_str, event)`, `install_hook(dest, command_str, event)`, `remove_hook(dest)`

### CLI Flags
```text
usage: install_antigravity_hooks.py [-h] [--scope {workspace,global,both}]
                                    [--workspace WORKSPACE]
                                    [--event {PostInvocation,Stop}] [--remove]

Configure Antigravity completion hooks (triggers linter when done).

options:
  -h, --help            show this help message and exit
  --scope {workspace,global,both}
                        Installation target scope
  --workspace WORKSPACE
                        Target workspace root
  --event {PostInvocation,Stop}
                        Lifecycle event (fires only when done, not on every
                        tool call)
  --remove              Uninstall the completion hook
```

## scripts/install_hooks.py
### Programmatic APIs
Functions: `create_hook_content()`, `install_hook(target_repo, action)`, `uninstall_hook(target_repo)`

### CLI Flags
```text
usage: install_hooks.py [-h] [--uninstall]
                        [--action {ask,overwrite,append,skip}]
                        [target]

Install claudemd_linter git pre-commit hook.

positional arguments:
  target                Target git repository path (default: current
                        directory)

options:
  -h, --help            show this help message and exit
  --uninstall           Uninstall pre-commit hook
  --action {ask,overwrite,append,skip}
```

## scripts/license_checker.py
### Programmatic APIs
Functions: `parse_requirements_txt(file_path)`, `parse_package_json(file_path)`, `parse_pyproject_toml(file_path)`, `get_pypi_license(package)`, `get_npm_license(package)`, `check_licenses(packages, registry)`

### CLI Flags
```text
usage: license_checker.py [-h]
```

## scripts/lint_fixer.py
### Programmatic APIs
Functions: `fix_line(line, lineno, path, fix_emojis, fix_banners)`, `condense_docstrings(content)`, `fix_file(path, dry_run, fix_emojis, fix_banners, fix_docstrings)`

### CLI Flags
```text
usage: lint_fixer.py [-h] [--dry-run] [--fix-emojis] [--no-banners]
                     [--fix-docstrings]
                     target

Apply guaranteed safe fixes for claudemd_linter.

positional arguments:
  target            File or directory to fix

options:
  -h, --help        show this help message and exit
  --dry-run         Preview fixes without modifying files
  --fix-emojis      Also safely strip unicode emojis (Rule 3)
  --no-banners      Disable heavy banner condensing (Rule 41)
  --fix-docstrings  Condense bloated docstrings on simple helpers (Rule 40)
```

## scripts/minify_instructions.py
### Programmatic APIs
Functions: `minify_text(text)`, `process_file(path, in_place, output_path)`

### CLI Flags
```text
usage: minify_instructions.py [-h] [-i] [-o OUTPUT] file

Minify AI instructions files for token efficiency.

positional arguments:
  file                  Path to instruction file (CLAUDE.md, .cursorrules,
                        etc.)

options:
  -h, --help            show this help message and exit
  -i, --in-place        Overwrite the original file directly
  -o OUTPUT, --output OUTPUT
                        Write to specified output file
```

## scripts/pack_context.py
### Programmatic APIs
Functions: `get_git_diff(staged)`, `get_symbol_map(ws)`, `pack_files(files, root, max_kb)`, `generate_summary(file_stats)`

### CLI Flags
```text
usage: pack_context.py [-h] [--diff] [--staged] [--symbols] [--output OUTPUT]
                       [--max-file-kb MAX_FILE_KB]
                       [files ...]

Package project context into a token-efficient prompt payload.

positional arguments:
  files                 Files to include in context package

options:
  -h, --help            show this help message and exit
  --diff                Include current git diff
  --staged              Include staged git diff
  --symbols             Include AST symbol tree
  --output OUTPUT       Output file path (default: stdout)
  --max-file-kb MAX_FILE_KB
                        Skip files larger than max KB
```

## scripts/prune_dead_code.py
### Programmatic APIs
Functions: `is_vulture_available()`, `find_unused_imports(file_path, preserve_init)`, `scan_dead_code_vulture(target)`, `prune_unused_imports_in_file(file_path, dry_run)`, `scan_directory(target, fix, include_vulture)`
Classes: `UnusedImport`, `DeadCodeItem`, `ASTUsageCollector`

### CLI Flags
```text
usage: prune_dead_code.py [-h] [--fix] [--dry-run] [--check] [--no-vulture]
                          [target]

Dead Code & Zombie Import Pruner (Deterministic & Safe AST Engine)

positional arguments:
  target        Target file or directory to scan (default: current directory)

options:
  -h, --help    show this help message and exit
  --fix         Safely remove unused imports in-place (verifies AST before
                saving)
  --dry-run     Preview changes without modifying files (default behavior)
  --check       Exit with code 1 if unused imports or dead code are found
  --no-vulture  Disable Vulture dead function/class scanning
```

## scripts/redact_diff.py
### Programmatic APIs
Functions: `run_git_diff(extra_args)`, `redact_diff_content(raw_diff, max_lines)`

### CLI Flags
```text
usage: redact_diff.py [-h] [--staged] [--commit COMMIT] [--stat]
                      [--max-lines MAX_LINES]
                      [git_args ...]

AST-aware token-compressor for git diff outputs

positional arguments:
  git_args              Additional arguments forwarded directly to git diff

options:
  -h, --help            show this help message and exit
  --staged              View staged changes (--cached)
  --commit COMMIT       Diff against specific commit (e.g. HEAD~1)
  --stat                Display token and line compression statistics
  --max-lines MAX_LINES, -m MAX_LINES
                        Hard line limit for output (default: 300)
```

## scripts/repo_map.py
### Programmatic APIs
Functions: `extract_python_symbols(path)`, `extract_regex_symbols(path)`, `generate_map(root, max_lines)`, `render_repo_map(root, max_lines)`

### CLI Flags
```text
usage: repo_map.py [-h] [--max-lines MAX_LINES] [--output OUTPUT] [path]

Generate compact AST symbol and dependency map.

positional arguments:
  path                  Root directory to analyze

options:
  -h, --help            show this help message and exit
  --max-lines MAX_LINES
                        Maximum lines in output (default: 300)
  --output OUTPUT, -o OUTPUT
                        Output file path (default: stdout)
```

## scripts/rollback.py
### Programmatic APIs
Functions: `get_checkpoint_dir(workspace)`, `list_checkpoints(ws)`, `save_checkpoint(ws, name)`, `restore_checkpoint(ws, name)`, `diff_checkpoint(ws, name)`, `clear_checkpoints(ws)`

### CLI Flags
```text
usage: rollback.py [-h] {save,restore,diff,list,clear} ...

Snapshot Checkpoint & Rollback Manager for AI Code Edits

positional arguments:
  {save,restore,diff,list,clear}
    save                Create an instant workspace checkpoint
    restore             Restore workspace to a checkpoint
    diff                View changes compared to a checkpoint
    list                List all available checkpoints
    clear               Clear all stored checkpoints

options:
  -h, --help            show this help message and exit
```

## scripts/schema_validator.py
### Programmatic APIs
Functions: `validate_type(data, expected_type)`, `validate_schema(data, schema, path)`, `validate_json_file(data_path, schema_path)`

### CLI Flags
```text
usage: schema_validator.py [-h] data schema

Validate JSON against JSON schema.

positional arguments:
  data        Path to JSON data file
  schema      Path to JSON schema file

options:
  -h, --help  show this help message and exit
```

## scripts/secret_sanitizer.py
### Programmatic APIs
Functions: `mask_secrets(text)`, `scan_file(path)`, `scan_directory(target)`

### CLI Flags
```text
usage: secret_sanitizer.py [-h] [--mask] [--stdin] [target]

Scan and mask credentials before AI prompt transmission.

positional arguments:
  target      Target file or directory

options:
  -h, --help  show this help message and exit
  --mask      Print file content with secrets masked
  --stdin     Read text from standard input and mask it
```

## scripts/slice_file.py
### Programmatic APIs
Functions: `get_file_slice(file_path, start, end, head, tail, numbered)`, `slice_lines(file_path, start, end, head, tail, numbered)`, `parse_range(range_str)`

### CLI Flags
```text
usage: slice_file.py [-h] [--head HEAD] [--tail TAIL] [--no-numbers]
                     target [range]

Inspect targeted line ranges of a file with line numbers

positional arguments:
  target        File path, optionally with range (e.g. main.py or
                main.py:50-100)
  range         Line range (e.g. 50-100, 50:, :100)

options:
  -h, --help    show this help message and exit
  --head HEAD   Show first N lines
  --tail TAIL   Show last N lines
  --no-numbers  Omit line numbers
```

## scripts/smart_test_runner.py
### Programmatic APIs
Functions: `get_git_modified_files(ws)`, `extract_symbols_from_file(path)`, `find_matching_tests(ws, modified_files)`, `find_venv_python(start_dir)`, `run_tests(test_files, ws, test_runner)`, `find_impacted_tests(changed_files)`

### CLI Flags
```text
usage: smart_test_runner.py [-h] [--workspace WORKSPACE] [--all] [--impacted]
                            [--runner {unittest,pytest}]
                            [files ...]

AST-aware test impact runner.

positional arguments:
  files                 Specific files or tests to run

options:
  -h, --help            show this help message and exit
  --workspace WORKSPACE
                        Workspace directory
  --all                 Run all discoverable tests
  --impacted            Run tests impacted by git diff
  --runner {unittest,pytest}
                        Test runner
```

## scripts/spell_checker.py
### Programmatic APIs
Functions: `split_identifier_words(token)`, `load_ignored_words(dict_path)`, `check_line_spelling(line, ignore)`, `audit_file_native(path, ignore)`, `run_external_typos(target)`, `scan_target(target, use_external, ignore)`

### CLI Flags
```text
usage: spell_checker.py [-h] [--native-only] [--dict DICT] [target]

Audit source code, comments, and docs for spelling errors.

positional arguments:
  target         Target file or directory

options:
  -h, --help     show this help message and exit
  --native-only  Bypass external typos tool
  --dict DICT    Path to custom dictionary file
```

## scripts/sync_rules.py
### Programmatic APIs
Functions: `get_rule_targets(ws)`, `find_most_recent_source(targets)`, `strip_frontmatter(content)`, `expand_template_variables(content)`, `format_for_target(target, expanded)`, `sync_rules(source, ws, dry_run)`

### CLI Flags
```text
usage: sync_rules.py [-h] [--source SOURCE] [--workspace WORKSPACE]
                     [--dry-run]

Synchronize rule files across all AI tools.

options:
  -h, --help            show this help message and exit
  --source SOURCE       Specific source file to copy from
  --workspace WORKSPACE
                        Target workspace path
  --dry-run             Preview sync actions without writing
```

## scripts/to_markdown.py
### Programmatic APIs
Functions: `extract_pdf_pypdf(pdf_path, max_pages)`, `extract_pdf_fallback(pdf_path, max_pages)`, `convert_pdf_to_md(pdf_path, max_pages)`, `convert_docx_to_md(docx_path)`, `convert_pptx_to_md(pptx_path, max_slides)`, `convert_csv_to_md(csv_path, max_rows)`, `convert_xlsx_to_md(xlsx_path, max_rows)`, `convert_ipynb_to_md(ipynb_path)`, `convert_html_to_md(html_path)`, `convert_file_to_markdown(file_path, max_pages, max_lines, include_meta)`
Classes: `SimpleHTMLToMarkdown`

### CLI Flags
```text
usage: to_markdown.py [-h] [--output OUTPUT] [--max-pages MAX_PAGES]
                      [--max-lines MAX_LINES] [--meta]
                      target

Universal Document to Structured Markdown Converter (PDF, DOCX, PPTX, XLSX,
CSV, IPYNB, HTML)

positional arguments:
  target                Path to document file to convert

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output file path (default: print to stdout)
  --max-pages MAX_PAGES, -p MAX_PAGES
                        Maximum pages/slides/sheets to parse
  --max-lines MAX_LINES, -l MAX_LINES
                        Maximum output lines to emit
  --meta                Prepend document YAML frontmatter metadata
```

## scripts/todo_finder.py
### Programmatic APIs
Functions: `clean_description(desc)`, `is_scannable_file(fpath)`, `scan_file(filepath)`, `scan_directory(target_path)`, `print_markdown_table(items)`, `print_summary(items)`, `parse_args(args)`
Classes: `TodoItem`

### CLI Flags
```text
usage: todo_finder.py [-h] [--markdown] [target]

Find TODOs in codebase.

positional arguments:
  target      Target path

options:
  -h, --help  show this help message and exit
  --markdown  Markdown format
```

## scripts/token_budget.py
### Programmatic APIs
Functions: `estimate_tokens(text)`, `analyze_file(path)`, `format_number(val)`, `scan_directory(target, max_depth)`, `format_token_distribution(file_token_counts, total_budget)`, `print_budget_report(results, root, threshold)`

### CLI Flags
```text
usage: token_budget.py [-h] [--threshold THRESHOLD] [--chart] [target]

Estimate token usage across files and directories.

positional arguments:
  target                Target file or directory path

options:
  -h, --help            show this help message and exit
  --threshold THRESHOLD
                        Token threshold to flag large files
  --chart               Display token distribution breakdown chart
```

## scripts/type_coverage.py
### Programmatic APIs
Functions: `analyze_file(filepath)`
Classes: `CoverageVisitor`

### CLI Flags
```text
usage: type_coverage.py [-h] [target]

Type Coverage Analyzer

positional arguments:
  target      Target directory or file

options:
  -h, --help  show this help message and exit
```

## scripts/unused_symbols.py
### Programmatic APIs
Functions: `analyze_file(filepath)`
Classes: `SymbolVisitor`

### CLI Flags
```text
usage: unused_symbols.py [-h] files [files ...]

Find unused private functions and local variables.

positional arguments:
  files       Files to analyze

options:
  -h, --help  show this help message and exit
```

## Test Execution Guidelines
The repository features an exhaustive 396-test pytest suite.
To execute tests locally with the proper environment configuration, run:
```bash
PYTHONPATH=. uv run --no-project pytest
```
Always ensure your code passes the full suite with an exit code of `0`.
