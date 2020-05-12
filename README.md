### Maze Navigation using BCI2000 P3Speller
#### EE Senior Design

Requires python 3.7 or above  
To build project:
```
git clone https://github.com/peter97mansour/BCI2000Maze.git
cd BCI2000Maze
pip install -r pkg_reqs.txt
cd src
python3 server.py [OPTIONS] IPV4_HOST [PORT]
python3 join_game.py [OPTIONS] IPV4_HOST [PORT] COLOR
```
To display options and usage, run:
```
python3 join_game.py --help
python3 server.py --help
```
