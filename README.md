# Calibre_Moly_hu
This [Calibre](https://calibre-ebook.com/) plugin has been created to download metadata and cover image from Moly.hu.

Original post from https://www.mobileread.com/forums/showthread.php?t=193302 by Kloon:
I must give credits to the original author, Daermond for making and publishing the initial plugin, but sadly he had abandoned it, so here I am taking over and fixing the errors that have popped up since.

Also, a big thumbs up for kiwidude, for sorting things out for me. 
And now an update by another author - fatsadt

## Main features:
Can retrieve title, author, series, ISBN, comments, tags, publisher, year of publication, rating and a cover images
Shows multiple results if possible (3 by default)
Search based on ISBN if present, otherwise based on title and/or author
Downloads multiple cover images if possible (5 by default)

## Special Notes:
Requires Calibre 0.8 or later. Tested with 3.2.0.0

## Installation Notes:
Download the attached zip file and install the plugin as described in the Introduction to plugins thread.
Note that this is not a GUI plugin so it is not intended/cannot be added to context menus/toolbars etc.

## Version History:
**Version 1.0.6** - 11 April 2018
The filter of relevant title and author by transliterate the extended Hungarian characters
Update by otapi

**Version 1.0.5** - 29 March 2018
Search was too wide, now filters only to relevant title and author
Update by otapi

**Version 1.0.4** - 25 Jan 2017
Now working again, and searches for ISBNs
Update by fatsadt

**Version 1.0.3** - 2 Jan 2014
Can download multiple bigger cover images now
Reworked the plugin configuration

**Version 1.0.2** - 28 Jul 2013
Patched plugin to work with the new layout of moly.hu
Now parses language as well, so calibre will no longer capitalize Hungarian book titles

**Version 1.0.1** - 9 Oct 2012
Fix for Moly.hu changes to html code
Parses ISBN, publisher, year of publication as well
Raised max number of results to 12

**Version 1.0** - 08 May 2011
Initial release of plugin
