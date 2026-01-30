# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 77b6cc15-a09f-47ea-9396-e6ba1febda9c -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Implement Memory Endpoint Integration
Replace placeholder memory endpoint in src/api/agents.py with actual Weaviate GraphQL queries.
- Review current placeholder code
- Implement Weaviate query logic
- Test endpoint returns real data
- Run pytest on agent API tests

### [x] Step: Implement Frontend Chat Component
Replace placeholder Chat component in src/web_ui/src/App.jsx with functional chat interface.
- Review existing React structure
- Implement chat UI with message display
- Add WebSocket integration for real-time messages
- Test component renders and connects

### [x] Step: Implement Frontend Config Component
Replace placeholder Config component in src/web_ui/src/App.jsx with functional configuration interface.
- Design config UI for agent settings
- Implement state management for config changes
- Add API calls to save/load config
- Test config persistence

### [x] Step: Add WebSocket Reconnection Logic
Implement auto-reconnection in src/web_ui/src/pages/Dashboard.jsx when WebSocket drops.
- Add reconnection state management
- Implement exponential backoff retry
- Handle connection errors gracefully
- Test reconnection on disconnect

### [x] Step: Add Rollback to Spirit Sync
Implement transaction rollback in src/core/identity/manager.py for failed sync operations.
- Review current sync logic
- Add database transaction wrapper
- Implement rollback on partial failures
- Test sync with failure scenarios

### [x] Step: Final Verification and Report
Run full test suite, lint, and type checks. Write implementation report.
- Execute pytest, pylint, mypy
- Manual verification of all features
- Write report.md with implementation details
