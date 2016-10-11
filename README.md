MegaCli64 is the command line utility provided by LSI for configuring raid
cards.  While all of the functionality is there, the interface can be
challenging to deal with.  Here are some examples:

 - case sensitivity + inconsistent case (example: `/opt/MegaRAID/MegaCli/MegaCli64 -LDInfo -Lall -aALL`)
 - inconsistent, hard-to-parse output (`BBU GasGauge Status: 0x0128`)
 - misleading summary information (components like BBUs will often simultaneously report `State: Optimal` and `Pack is about to fail & should be replaced`, which seems like they should never occur at the same time)

This library seeks to wrap MegaCli and MegaCli64 and provide an object-oriented interface
to see what the heck is actually going on with your controller.

At this time, it doesn't support CHANGING anything, just displaying data. This makes it
suitable to use in, e.g., nagios checks, but you still have to remember how to actually
change settings. That might change in the future.
