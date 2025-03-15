pvedaemon(8)
Proxmox Server Solutions GmbH
<support@proxmox.com>
version 8.3.1, Wed Nov 20 21:19:42 CET 2024
NAME 
pvedaemon - PVE API Daemon

SYNOPSIS 
pvedaemon <COMMAND> [ARGS] [OPTIONS]

pvedaemon help [OPTIONS]

Get help about specified command.

--extra-args <array>
Shows help for a specific command

--verbose <boolean>
Verbose output format.

pvedaemon restart

Restart the daemon (or start if not running).

pvedaemon start [OPTIONS]

Start the daemon.

--debug <boolean> (default = 0)
Debug mode - stay in foreground

pvedaemon status

Get daemon status.

pvedaemon stop

Stop the daemon.