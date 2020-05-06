### Maze Navigation using BCI2000 P3Speller
#### EE Senior Design

Requires python 3.x

You need to pip install:
 - click 7.1.1
 - numpy 1.18.2
 - Pillow 7.1.0
 - PyBluez-win10

To run server:
	`python3 server.py [OPTIONS] IPV4_HOST [PORT]`

To join game:
	`python3 join_game.py [OPTIONS] IPV4_HOST [PORT] COLOR BCI2000_APP_LOG_PATH`

To display options and usage, run:
`python3 join_game.py --help`
`python3 server.py --help`
