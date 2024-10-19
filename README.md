# README - BETA mælaborð fyrir Sigurð Erni með SHINY

## Keyrsla

Nú höfum við gert **BETA** útgáfu sem hægt er að keyra svona:

### Setja upp umhverfi

Keyrðu þetta í skelinni til þess að setja upp umhverfi

```bash
pip install -r requirements.txt
```

Þá áttu að geta keyrt `siggi_app.py` svona:

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
