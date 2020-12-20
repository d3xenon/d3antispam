# d3antispam

Пример простого алгоритма, обнаруживающего (и в меру возможностей наказывающего) спам на d3.ru

## Пример использования
~~~~
$ export D3USER=YourUsername
$ export D3PASS='YourPassword'
$ ./d3antispam.py --period 5h --body 'SPAM DETECTED! https://github.com/d3xenon/d3antispam'
~~~~

## Ограничения
- d3antispam не может удалять посты (т.к. мою юзер этого не может)
- d3 имеет ограничение на количество логина-минусований-комментариев в короткий период времени (d3antispam просто игнорирует ошибку). 

## Протокол работы

https://gist.github.com/d3xenon/7e1cd876f4e1b6b425a936197a14d9ca
