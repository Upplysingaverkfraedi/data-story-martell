#  Mælaborð fyrir Sigurð Erni með SHINY

## Keyrsla

Við notum `activeaapp.py` sem notar gagnagrunnin `siggi_timataka.db`. Hægt er að keyra svona:

### Setja upp umhverfi

Keyrðu þetta í skelinni til þess að setja upp umhverfi

```bash
pip install -r requirements.txt
```

Þá áttu að geta keyrt `activationapp.py` svona:

```bash
shiny run --reload siggi_app.py
```

Þá ættiru að fá upp þetta: 

```bash
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [9478] using WatchFiles
INFO:     Started server process [9482]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Cppyaðu** `http://127.0.0.1:8000` og **pasteaðu** í vafranum þínum t.d. safari eða chrome, og þá ættiru að sjá **BETA** útgáfunum af mælaborðnum.

## Mælaborð

### 1. Mælaborð 
Þetta mælaborð sýnir sætin sem að hlauparinn hefur lent í í öllum hluapunum sem hann hefur tekið þátt í sem eru á `timataka.net`

### 2. Mælaborð
Þetta mælaborð sýnir hvaða hlaupum hann hefur keppt í og hversu oft

### 3. Mælaborð
Þetta mælaborðið sýnir hvernig hann hefur bætt sig í þeirri tegund af hlaupi sem valið er.

### 4. Mælaborð 
Sýnir í hvaða sæti hann hefur lent í í hverju hlaupi.

## Stutt um ferli

Ferlið er búið að vera strembið en ég sótti alla linka af `timataka.net` og sigtaði þá niður í þannig ég hafði aðeins n`Overall` niðurstöður og sem hægt var að finna töflur úr. 

Síðan notaði `timataka.py` úr seinasta verkefni og bjó til `.csv` skrár. Eftir það þurfti ég að hreisa þær vel en ég ákvað að nota python til þess að sigta gögnin enþá meira þannig að við höfðum aðeins upplýsingar um `Sigurjón Ernir Sturluson` og bjó til aðrar `.csv` skrár til þess að einfalda það að færa yfir í gagnagrunn. 

Eftir það setti ég gögnin í gagnagrunn og með `SQL` kóða þannig að ég hafði viðeigandi töflur sem ég gat vísað í og notað í `Shiny`. Eftir það gat ég nota `python` og gert `Shiny` viðmót sem þið getið núna skoðað

Veit þetta eru miklar upplýsingar en ég mun reyna að setja ferlið á skiljanlegri hátt fyrir skil.

Hægt er að skoðað töflur í gagnagrunninum `siggi_timataka.db` með:
```SQL
.tables
```
Þið getið líka skoðað dálka i töflum sem þið viljið skoða með þessu:
```sql
PRAGMA table_info(timataka);
```
og skoðað töflurnar svona:

```sql
SELECT * FROM table
```
þar sem `table` er tafla sem þið viljið skoða
