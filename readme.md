Livelogs
========

Livelogs is a log parsing system developed initially for Team Fortress 2,
written in Python, PHP and JavaScript.

It receives log output via [SRCDS](https://developer.valvesoftware.com/wiki/
Source_Dedicated_Server) UDP logging, and parses the logs realtime. By
using a queueing system and smart processing, hundreds of logs can be parsed
simultaeneously. 

Logs being parsed in realtime can be viewed via a webpage, which will also 
update data as it is parsed.

Website
-------

The website is rather simple, and written in PHP/JavaScript. JavaScript is
used for [WebSockets](http://en.wikipedia.org/wiki/WebSocket) and processing 
live updates.

Parser
------
The parser is written in Python, and employs a daemon which listens for 
log requests. If the client has a valid API key, a new listen object is
created, which receives the log data and runs it through the parser. The
parser uses regular expressions to match log output, and inserts the data
into a PostreSQL database using a queue.


