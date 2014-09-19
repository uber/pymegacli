If you have any LSI RAID cards in your infrastructure which predate the acquisition
of 3ware, you are undoubtedly familiar with MegaCli64, the horrible program which LSI
provides for administrating these cards. Its lack of user-friendliness is legendary. Some
egregious examples:

 - case sensitivity + inconsistent case (example: `/opt/MegaRAID/MegaCli/MegaCli64 -LDInfo -Lall -aALL`)
 - wildly inconsistent, hard-to-parse output (`BBU GasGauge Status: 0x0128`)
 - misleading summary information (components like BBUs will often simultaneously report `State: Optimal` and `Pack is about to fail & should be replaced`, which seems like they should never occur at the same time)

This library seeks to wrap MegaCli and MegaCli64 and provide an object-oriented interface
to see what the heck is actually going on with your controller.

At this time, it doesn't support CHANGING anything, just displaying data. This makes it
suitable to use in, e.g., nagios checks, but you still have to remember how to actually
change settings. That might change in the future.
