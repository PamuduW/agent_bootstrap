#!/usr/bin/env bash
# shellcheck shell=bash

agentbot_menu_status() {
	local status_rc=0 doctor_rc=0
	agentbot_run_backend status || status_rc=$?
	agentbot_run_backend doctor || doctor_rc=$?
	if ((status_rc != 0)); then
		return "$status_rc"
	fi
	return "$doctor_rc"
}

agentbot_menu_doctor() {
	agentbot_menu_status
}
