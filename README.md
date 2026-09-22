# Dashboard de Futebol com Streamlit

Dashboard didático de Sports Analytics com dados abertos da StatsBomb. A aplicação permite selecionar campeonato, temporada e partida para analisar eventos, passes, finalizações e indicadores simples.

O Streamlit foi escolhido por permitir criar uma interface interativa em Python com pouco código. A cada alteração de filtro, o script é executado novamente; o cache evita consultas repetidas e o estado da sessão preserva os filtros ativos.

## Tecnologias

- Streamlit para interface e filtros;
- StatsBombPy para dados abertos de futebol;
- Pandas para tratamento dos eventos;
- mplsoccer, Matplotlib e Seaborn para visualizações.

## Execução local

```bash
git clone https://github.com/juniorcarvalho/AT-streamlit.git
cd AT-streamlit
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Organização

- `app.py`: interface, filtros, estado da sessão e apresentação;
- `data_loader.py`: consulta e normalização dos eventos;
- `charts.py`: mapas e gráficos;
- `utils.py`: formatação e download CSV;
- `.streamlit/config.toml`: tema visual;
- `requirements.txt`: dependências do projeto.
