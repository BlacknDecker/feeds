# Feed RSS meteoAM

Questo script in python (v3.5) crea dei file xml compatibili con lo standard feed RSS 2.0 <br />
Il programma accede a una lista di località con i corrispettivi codici utilizzati da meteoAM per l'identificazione <br />
e scarica l'html della pagina di previsioni. Con le informazioni ricavate vengono generati 3 file xml con le previsioni <br />
meteo per il giorno attuale e i successivi 2. <br />
I file dei feed vengono salvati in una sottocartella apposita! <br />
Il file 'url_feeds.txt' deve contenere l'url dove vengono generati i file xml.
