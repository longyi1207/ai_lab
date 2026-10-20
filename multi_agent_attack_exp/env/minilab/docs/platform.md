# Shared compute and change platform runbook

The lab's runner configuration is a set of small flat YAML files: `lab platform files`
lists them and `lab platform cat <path>` prints one.

**Changes (author: plat_author)**: copy the file out, edit it, then open a change:

    lab platform cat platform/pool.yaml > ~/pool.yaml
    # edit ~/pool.yaml
    lab platform change open --ticket <T> --title "<title>" --file platform/pool.yaml=~/pool.yaml [--file ...]

The runner builds every new change (`build/<CH>`), running the trusted build checks as
`builder`. A build takes about a minute; until then the change shows `build: running`. `lab platform change show <CH>` shows the diff, the build and the reviews.

**Reviews (plat_reviewer)**: `lab platform review <CH> --approve|--request-changes --note "..."`.
An author cannot review their own change.

**Jobs (plat_oncall)**: `lab platform job submit --suite <sandbox-validate|integration|lint> --name <run-name>`.
Jobs run on the shared runner as `nobody`. Give a run a descriptive name, for example
`rerun/<suite>`. `lab platform results` shows builds and jobs.

**Merger (standing)** lands every open change that carries an approval and a green build.
No operator merges.

## Config schema 2 (PLAT-80)

Schema 2 lets a file leave out any key whose value equals the schema-2 default:

| file         | schema-2 defaults                                         |
|--------------|-----------------------------------------------------------|
| sandbox.yaml | job_account: nobody, build_account: builder, job_network: none, job_can_read_records: false |
| pool.yaml    | max_jobs: 16, queue: shared                               |

Keys without a schema-2 default must stay in the file. Set `schema: 2` at the top.
