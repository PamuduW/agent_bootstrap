#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2016,SC2088  # Literal paths and variable expressions are documentation values.
# Authoritative public Agentbot command, configuration, and surface catalog.

AGENTBOT_COMMAND_KEYS=(
	status install update token boot workspace workspaces resync command_lib doctor dotfiles
)
AGENTBOT_BACKEND_COMMAND_KEYS=(
	install 'skills install' 'skills update' 'skills upgrade' 'skills list' 'skills doctor'
	doctor update status global workspace workspaces resync
)
AGENTBOT_CONFIG_KEYS=(
	AGENTBOT_HOME XDG_CONFIG_HOME GITHUB_TOKEN AGENTBOT_TUI AGENTBOT_QUIET
	AGENTBOT_MENU_COLS DOTFILES_HOME
)
AGENTBOT_SURFACE_KEYS=(canonical_sources rendered_outputs skill_store workspace_registry github_config)

declare -A AGENTBOT_COMMAND_USAGE=(
	[status]='agentbot status [--json]'
	[install]='agentbot install'
	[update]='agentbot update|upgrade [--dry-run] [--yes]'
	[token]='agentbot token'
	[boot]='agentbot boot [--agents|--codex|--claude|--copilot|--cursor] [--profile NAME] [TARGET]'
	[workspace]='agentbot workspace [--profile NAME] [--targets LIST] [--yes] PATH'
	[workspaces]='agentbot workspaces'
	[resync]='agentbot resync [--all | PATH ...] [--yes|--dry-run]'
	[command_lib]='Agentbot menu: Command Lib'
	[doctor]='agentbot doctor'
	[dotfiles]='agentbot dotfiles'
)

declare -A AGENTBOT_COMMAND_CLASS=(
	[status]='read-only'
	[install]='mutating'
	[update]='mutating'
	[token]='mutating'
	[boot]='mutating'
	[workspace]='mutating'
	[workspaces]='read-only'
	[resync]='mutating'
	[command_lib]='read-only'
	[doctor]='read-only'
	[dotfiles]='mutating'
)

declare -A AGENTBOT_COMMAND_ENTRYPOINT=(
	[status]='agentbot wrapper -> ./install.sh status'
	[install]='agentbot wrapper -> ./install.sh install'
	[update]='agentbot wrapper -> ./install.sh update'
	[token]='Agentbot token configuration seam'
	[boot]='Agentbot wrapper -> workspace --yes'
	[workspace]='Agentbot wrapper -> Python workspace engine'
	[workspaces]='Agentbot wrapper -> Python workspace engine'
	[resync]='Agentbot wrapper -> Python workspace engine'
	[command_lib]='Agentbot menu reference'
	[doctor]='agentbot wrapper -> ./install.sh doctor'
	[dotfiles]='Agentbot -> sibling Dotfiles bridge seam'
)

declare -A AGENTBOT_COMMAND_SUMMARY=(
	[status]='Show Agentbot health, installed skills, and rendered baseline state.'
	[install]='Install skills, refresh outputs, run Doctor, and link Agentbot.'
	[update]='Run the repo-first update and reconcile source-owned skills.'
	[token]='Configure the optional shared GitHub API token.'
	[boot]='Create or preserve agent policy files in a target repository.'
	[workspace]='Preview or render one registered workspace.'
	[workspaces]='List locally registered workspaces.'
	[resync]='Preview or refresh registered workspaces.'
	[command_lib]='Show this complete command and configuration reference.'
	[doctor]='Validate skills, rendered outputs, links, and configuration.'
	[dotfiles]='Open the sibling Dotfiles installer when the bridge is available.'
)

declare -A AGENTBOT_COMMAND_OPTIONS=(
	[status]=$'--json|Emit machine-readable status for the Python backend path.|off'
	[install]=$'(none)|The explicit install flow takes no wrapper options.|always'
	[update]=$'--dry-run|Preview repo-first reconciliation without writing source-owned files.|off\n--yes|Confirm source-owned changes after the preview.|off'
	[token]=$'(none)|The token screen is a configuration seam and does not accept flags.|always'
	[boot]=$'--agents|Include the canonical AGENTS.md output; it is always included.|always\n--codex|Alias for --agents; it does not create a second output.|alias\n--claude|Include generated Claude output.|selected by default\n--copilot|Include generated Copilot instructions.|opt-in\n--cursor|Include generated Cursor rules.|selected by default\n--profile NAME|Select a workspace profile before rendering.|unset\nTARGET|Writable target directory for the generated files.|current directory'
	[workspace]=$'--profile NAME|Select a workspace profile.|unset\n--targets LIST|Comma-separated outputs: agents,claude,copilot,cursor; codex aliases agents.|all enabled outputs\n--yes|Apply and register the render; without it the command previews.|preview only\nPATH|Workspace directory to preview or render.|required'
	[workspaces]=$'(none)|This command lists registered workspaces and takes no options.|always'
	[resync]=$'--all|Include every enabled registered workspace.|mutually exclusive with PATH\n--yes|Apply Agentbot-managed changes.|preview by default\n--dry-run|Preview without writing; mutually exclusive with --yes.|preview by default\nPATH ...|Refresh only the listed registered workspaces.|required unless --all'
	[command_lib]=$'(none)|The Command Lib is read-only and takes no options.|always'
	[doctor]=$'(none)|Doctor reads state and reports issues; it takes no options.|always'
	[dotfiles]=$'(none)|The bridge opens the sibling installer when that integration is installed.|always'
)

declare -A AGENTBOT_COMMAND_DEFAULTS=(
	[status]='Reads the current Agentbot installation and global render state.'
	[install]='Runs the explicit installation flow.'
	[update]='Requires the repository-first update gate before reconciliation.'
	[token]='No token is required; GitHub API calls can remain unauthenticated.'
	[boot]='TARGET defaults to the current directory; agents, claude, and cursor are selected by default; copilot is opt-in with --copilot.'
	[workspace]='Without --yes the workspace is previewed and not registered.'
	[workspaces]='Reads the local registry at the configured Agentbot path.'
	[resync]='Requires --all or at least one registered PATH; preview is safe by default.'
	[command_lib]='Prints the complete catalog without changing state.'
	[doctor]='Reports issues without repairing them.'
	[dotfiles]='Requires a resolvable sibling Dotfiles installer.'
)

declare -A AGENTBOT_COMMAND_EFFECTS=(
	[status]='Reads skills, lock, render, link, and doctor state.'
	[install]='May install skills, render global files, run Doctor, and create the Agentbot link.'
	[update]='May pull/reconcile source-owned skills and refresh rendered outputs after confirmation.'
	[token]='Writes the token outside the repository when configured; the value is never displayed here.'
	[boot]='May write AGENTS.md and selected agent-specific outputs in TARGET.'
	[workspace]='Preview reads target files; --yes writes selected outputs and updates the registry.'
	[workspaces]='Reads the local workspace registry only.'
	[resync]='Preview reads registered targets; --yes may update their managed files and registry.'
	[command_lib]='Performs no external command, file, network, or installer action.'
	[doctor]='Reads installed skills, rendered outputs, links, and configuration.'
	[dotfiles]='May leave Agentbot and launch the sibling Dotfiles menu; availability is checked first.'
)

declare -A AGENTBOT_COMMAND_EXAMPLES=(
	[status]='agentbot status'
	[install]='agentbot install'
	[update]='agentbot update --dry-run'
	[token]='agentbot token'
	[boot]='agentbot boot --claude --profile personal /path/to/repo'
	[workspace]='agentbot workspace --targets agents,claude --yes /path/to/repo'
	[workspaces]='agentbot workspaces'
	[resync]='agentbot resync --all --dry-run'
	[command_lib]='Select Command Lib from the Agentbot menu'
	[doctor]='agentbot doctor'
	[dotfiles]='agentbot dotfiles'
)

declare -A AGENTBOT_COMMAND_RELATED=(
	[status]='Use doctor for validation; use update when changes are intended.'
	[install]='Run status or doctor afterward to inspect the result.'
	[update]='Use --dry-run first; install is the full first-time flow.'
	[token]='The token is used by GitHub API helpers during skill/release operations.'
	[boot]='Uses the workspace renderer; workspace is the lower-level preview/apply command.'
	[workspace]='Use workspaces to inspect registrations; resync to refresh several.'
	[workspaces]='Use resync to preview or apply changes to registered paths.'
	[resync]='Use workspace for one path or workspaces to inspect the registry.'
	[command_lib]='The same catalog is available through agentbot help.'
	[doctor]='Use status for a non-diagnostic snapshot.'
	[dotfiles]='The reciprocal entry is exposed by the Dotfiles Agents menu.'
)

declare -A AGENTBOT_BACKEND_USAGE=(
	[install]='./install.sh install'
	['skills install']='./install.sh skills install'
	['skills update']='./install.sh skills update'
	['skills list']='./install.sh skills list'
	['skills doctor']='./install.sh skills doctor'
	[doctor]='./install.sh doctor'
	[update]='./install.sh update|upgrade [--dry-run] [--yes]'
	['skills upgrade']='./install.sh skills upgrade'
	[status]='./install.sh status [--json]'
	[global]='./install.sh global'
	[workspace]='./install.sh workspace [--profile NAME] [--targets LIST] [--yes] PATH'
	[workspaces]='./install.sh workspaces'
	[resync]='./install.sh resync [--all | PATH ...] [--yes|--dry-run]'
)

declare -A AGENTBOT_BACKEND_SUMMARY=(
	[install]='Run the complete first-time Agentbot installation.'
	['skills install']='Install enabled upstream skills from skills.sources.yaml.'
	['skills update']='Refresh globally installed skills from the skill lock.'
	['skills upgrade']='Alias for refreshing globally installed skills from the skill lock.'
	['skills list']='List installed skills under the global skill store.'
	['skills doctor']='Validate skill sources, tooling, and lock prerequisites.'
	[doctor]='Validate the slim global baseline and installed skills.'
	[update]='Run repository-first source-owned skill reconciliation.'
	[status]='Show skill and global-render status.'
	[global]='Render global agent outputs from canonical sources.'
	[workspace]='Preview or apply one workspace through the Python engine.'
	[workspaces]='List locally registered workspaces.'
	[resync]='Preview or apply registered workspace refreshes.'
)

declare -A AGENTBOT_BACKEND_OPTIONS=(
	[install]=$'(none)|The complete install command takes no options.|always'
	['skills install']=$'(none)|Installs the enabled manifest entries.|always'
	['skills update']=$'(none)|Refreshes the global skill store from the lock file.|always'
	['skills upgrade']=$'(none)|Alias for refreshing the global skill store from the lock file.|always'
	['skills list']=$'(none)|Lists installed skills without changing them.|always'
	['skills doctor']=$'(none)|Validates skill prerequisites without changing them.|always'
	[doctor]=$'(none)|Runs the slim Doctor checks.|always'
	[update]=$'--dry-run|Preview reconciliation without writing.|off\n--yes|Confirm source-owned changes.|off'
	[status]=$'--json|Emit machine-readable status from the Python workspace engine.|off'
	[global]=$'(none)|Renders global outputs from canonical sources.|always'
	[workspace]=$'--profile NAME|Select a workspace profile.|unset\n--targets LIST|Select comma-separated outputs; codex aliases agents.|all enabled outputs\n--yes|Apply and register instead of previewing.|preview only\nPATH|Workspace directory.|required'
	[workspaces]=$'(none)|Lists registered workspaces.|always'
	[resync]=$'--all|Include all enabled registered workspaces.|mutually exclusive with PATH\n--yes|Apply managed changes.|preview by default\n--dry-run|Preview without writing.|preview by default\nPATH ...|Explicit registered workspace paths.|required unless --all'
)

declare -A AGENTBOT_CONFIG_DESCRIPTION=(
	[AGENTBOT_HOME]='Validated Agentbot repository root used by the wrapper and backend.'
	[XDG_CONFIG_HOME]='Base directory for private Agentbot configuration and registries.'
	[GITHUB_TOKEN]='Optional GitHub API credential used for authenticated release/source requests.'
	[AGENTBOT_TUI]='Marks menu-driven execution so backend reports use the TUI presentation.'
	[AGENTBOT_QUIET]='Suppresses selected non-interactive backend report output.'
	[AGENTBOT_MENU_COLS]='Overrides the detected Agentbot menu width for rendering/tests.'
	[DOTFILES_HOME]='Optional validated sibling Dotfiles repository override.'
)

declare -A AGENTBOT_CONFIG_DEFAULT=(
	[AGENTBOT_HOME]='Resolved from the executable path unless explicitly exported.'
	[XDG_CONFIG_HOME]='$HOME/.config when unset.'
	[GITHUB_TOKEN]='Unset; API helpers fall back to unauthenticated requests.'
	[AGENTBOT_TUI]='Unset for direct commands; set to 1 by the Agentbot menu.'
	[AGENTBOT_QUIET]='Unset.'
	[AGENTBOT_MENU_COLS]='Detected terminal width, otherwise 80.'
	[DOTFILES_HOME]='Sibling dotfiles directory next to AGENTBOT_HOME.'
)

declare -A AGENTBOT_CONFIG_LOCATION=(
	[AGENTBOT_HOME]='Process environment; repository root.'
	[XDG_CONFIG_HOME]='Process environment; ${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/.'
	[GITHUB_TOKEN]='Process environment or ${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/github.env.'
	[AGENTBOT_TUI]='Process environment only.'
	[AGENTBOT_QUIET]='Process environment only.'
	[AGENTBOT_MENU_COLS]='Process environment only.'
	[DOTFILES_HOME]='Process environment; sibling repository path.'
)

declare -A AGENTBOT_SURFACE_DESCRIPTION=(
	[canonical_sources]='Canonical policy/templates that own generated agent instructions.'
	[rendered_outputs]='Global and repository-local AGENTS/CLAUDE/Copilot/Cursor outputs.'
	[skill_store]='Installed skills and the authoritative global skill lock.'
	[workspace_registry]='Private registry of workspaces known to Agentbot.'
	[github_config]='Private optional GitHub token configuration; secret values are not shown.'
)

declare -A AGENTBOT_SURFACE_LOCATION=(
	[canonical_sources]='agent_bootstrap/base/ and agent_bootstrap/global/'
	[rendered_outputs]='~/.codex/AGENTS.md, ~/.claude/*, and selected target-repo files'
	[skill_store]='~/.agents/skills/ and ~/.agents/.skill-lock.json'
	[workspace_registry]='${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/workspaces.json'
	[github_config]='${XDG_CONFIG_HOME:-$HOME/.config}/agentbot/github.env'
)

agentbot_command_catalog_validate() {
	local key class option description default
	local -A seen=()

	for key in "${AGENTBOT_COMMAND_KEYS[@]}"; do
		[[ -n "$key" && -z "${seen[$key]+x}" ]] || return 1
		seen["$key"]=1
		[[ -n "${AGENTBOT_COMMAND_USAGE[$key]:-}" ]] || return 1
		class="${AGENTBOT_COMMAND_CLASS[$key]:-}"
		[[ "$class" == read-only || "$class" == mutating ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_ENTRYPOINT[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_SUMMARY[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_DEFAULTS[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_EFFECTS[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_EXAMPLES[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_COMMAND_RELATED[$key]:-}" ]] || return 1
		while IFS='|' read -r option description default; do
			[[ -z "$option" && -z "$description" && -z "$default" ]] && continue
			[[ -n "$option" && -n "$description" && -n "$default" ]] || return 1
		done <<<"${AGENTBOT_COMMAND_OPTIONS[$key]:-}"
	done

	for key in "${AGENTBOT_BACKEND_COMMAND_KEYS[@]}"; do
		[[ -n "${AGENTBOT_BACKEND_USAGE[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_BACKEND_SUMMARY[$key]:-}" ]] || return 1
		while IFS='|' read -r option description default; do
			[[ -z "$option" && -z "$description" && -z "$default" ]] && continue
			[[ -n "$option" && -n "$description" && -n "$default" ]] || return 1
		done <<<"${AGENTBOT_BACKEND_OPTIONS[$key]:-}"
	done

	for key in "${AGENTBOT_CONFIG_KEYS[@]}"; do
		[[ -n "${AGENTBOT_CONFIG_DESCRIPTION[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_CONFIG_DEFAULT[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_CONFIG_LOCATION[$key]:-}" ]] || return 1
	done
	for key in "${AGENTBOT_SURFACE_KEYS[@]}"; do
		[[ -n "${AGENTBOT_SURFACE_DESCRIPTION[$key]:-}" ]] || return 1
		[[ -n "${AGENTBOT_SURFACE_LOCATION[$key]:-}" ]] || return 1
	done
	[[ "${#seen[@]}" -eq "${#AGENTBOT_COMMAND_KEYS[@]}" ]]
}
