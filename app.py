from __future__ import annotations

import pandas as pd
import streamlit as st

from charts import build_subplots_for_match_statistics, plot_event_distribution, plot_pass_map, plot_passes_vs_goals, plot_player_comparison, plot_shot_map
from data_loader import build_match_summary, filter_events_by_player, load_competitions, load_match_events, load_matches, load_players, load_seasons, normalize_events
from utils import download_csv_button, format_match_metadata


st.set_page_config(page_title="Dashboard de Futebol - StatsBomb", layout="wide")


@st.cache_data(show_spinner=False)
def get_competitions() -> pd.DataFrame:
    return load_competitions()


@st.cache_data(show_spinner=False)
def get_seasons(competition_id: int) -> pd.DataFrame:
    return load_seasons(competition_id)


@st.cache_data(show_spinner=False)
def get_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    return load_matches(competition_id, season_id)


@st.cache_data(show_spinner=False)
def get_events(match_id: int) -> pd.DataFrame:
    return normalize_events(load_match_events(match_id))


def render_filters(competitions: pd.DataFrame):
    st.sidebar.header("Filtros")
    st.sidebar.caption("Escolha a competição, a temporada e a partida.")
    competition_ids = competitions["competition_id"].astype(int).drop_duplicates().tolist()
    competition_lookup = competitions.drop_duplicates("competition_id").set_index("competition_id")
    competition_id = st.sidebar.selectbox(
        "Campeonato",
        competition_ids,
        format_func=lambda value: f"{competition_lookup.loc[value, 'competition_name']} ({competition_lookup.loc[value, 'country_name']})",
    )
    seasons = get_seasons(int(competition_id))
    if seasons.empty:
        st.sidebar.warning("Não há temporadas disponíveis para este campeonato.")
        return None, None, None
    season_ids = seasons["season_id"].astype(int).tolist()
    season_lookup = seasons.set_index("season_id")["season_name"]
    season_id = st.sidebar.selectbox("Temporada", season_ids, format_func=lambda value: season_lookup.loc[value])
    matches = get_matches(int(competition_id), int(season_id))
    if matches.empty:
        st.sidebar.warning("Não há partidas disponíveis para esta temporada.")
        return None, None, None
    match_ids = matches["match_id"].astype(int).tolist()
    match_lookup = matches.set_index("match_id")
    match_id = st.sidebar.selectbox(
        "Partida",
        match_ids,
        format_func=lambda value: f"{match_lookup.loc[value, 'home_team']} x {match_lookup.loc[value, 'away_team']} — {match_lookup.loc[value, 'match_date']}",
    )
    return competition_lookup.loc[competition_id], season_lookup.loc[season_id], match_lookup.loc[match_id]


def render_dashboard(events_df: pd.DataFrame, match: pd.Series, competition: pd.Series, season_name: str):
    players = ["Todos", *load_players(events_df)]
    event_types = sorted(events_df["event_type"].dropna().unique().tolist())
    teams = ["Todos", match["home_team"], match["away_team"]]
    page = st.sidebar.radio("Navegação", ["Análise da partida", "Comparação de jogadores"])
    event_limit_min = min(10, len(events_df))
    event_limit_max = len(events_df)
    event_limit_default = min(100, event_limit_max)
    if "event_limit" in st.session_state:
        st.session_state["event_limit"] = max(
            event_limit_min,
            min(st.session_state["event_limit"], event_limit_max),
        )
    with st.sidebar.form("event_filters"):
        player_name = st.selectbox("Jogador", players, key="selected_player")
        selected_types = st.multiselect("Tipos de evento", event_types, default=event_types, key="selected_event_types")
        team_name = st.radio("Equipe nos mapas", teams, key="selected_team")
        event_limit = st.slider(
            "Quantidade de eventos exibidos",
            min_value=event_limit_min,
            max_value=event_limit_max,
            value=event_limit_default,
            key="event_limit",
        )
        include_coordinates = st.checkbox("Exibir coordenadas na tabela", value=False, key="include_coordinates")
        st.form_submit_button("Aplicar filtros")
    filtered = events_df.loc[events_df["event_type"].isin(selected_types)].copy()
    filtered = filter_events_by_player(filtered, player_name).head(event_limit)
    summary_events = filter_events_by_player(events_df, player_name)
    summary = build_match_summary(summary_events)
    summary_scope = "do jogador selecionado" if player_name != "Todos" else "da partida"
    conversion_display = f"{summary['shot_conversion']:.1f}".rstrip("0").rstrip(".")
    st.subheader(format_match_metadata(match.to_dict()))
    st.caption(f"{competition['competition_name']} — temporada {season_name}")
    st.caption(f"Indicadores {summary_scope}.")

    if page == "Comparação de jogadores":
        render_player_comparison(events_df)
        return

    metrics = st.columns(4)
    metrics[0].metric("Gols", summary["total_goals"])
    metrics[1].metric("Chutes", summary["total_shots"])
    metrics[2].metric("Passes completos", summary["successful_passes"], f"de {summary['total_passes']} passes")
    metrics[3].metric("Conversão", f"{conversion_display}%")

    summary_tab, charts_tab, data_tab = st.tabs(["Resumo", "Gráficos", "Dados"])
    with summary_tab:
        st.header("Leitura da partida")
        st.text(f"Eventos carregados: {summary['event_count']}")
        summary_table = pd.DataFrame([summary]).rename(columns={"total_goals": "gols", "total_shots": "chutes", "total_passes": "passes", "successful_passes": "passes completos", "shot_conversion": "conversão (%)", "event_count": "eventos"})
        st.table(summary_table.style.format({"conversão (%)": "{:.1f}"}))
    with charts_tab:
        selected_team = "" if team_name == "Todos" else team_name
        chart_events = filtered if not filtered.empty else events_df.iloc[0:0]
        map_left, map_right = st.columns(2)
        with map_left:
            st.pyplot(plot_pass_map(chart_events, selected_team), use_container_width=True)
        with map_right:
            st.pyplot(plot_shot_map(chart_events, selected_team), use_container_width=True)
        for chart in (plot_event_distribution(filtered), plot_passes_vs_goals(events_df), plot_player_comparison(events_df), build_subplots_for_match_statistics(events_df)):
            if chart is not None:
                st.pyplot(chart, use_container_width=True)
    with data_tab:
        st.subheader("Eventos filtrados")
        columns = ["minute", "event_type", "team_name", "player_name", "outcome", "pass_length", "shot_xg"]
        if include_coordinates:
            columns.extend(["x", "y", "end_x", "end_y"])
        st.dataframe(filtered[columns], use_container_width=True, hide_index=True)
        download_csv_button(filtered)


def render_player_comparison(events_df: pd.DataFrame):
    """Renderiza uma visão simples de comparação entre jogadores da partida."""
    st.header("Comparação por jogador")
    st.write("Compare volume de passes, acerto e finalizações dos jogadores da partida.")
    players = load_players(events_df)
    if not players:
        st.info("Não há jogadores disponíveis para comparação.")
        return
    selected_players = st.multiselect("Jogadores", players, default=players[: min(2, len(players))])
    comparison_events = events_df.loc[events_df["player_name"].isin(selected_players)]
    passes = comparison_events.loc[comparison_events["event_type"].eq("Pass")]
    shots = comparison_events.loc[comparison_events["event_type"].eq("Shot")]
    comparison = pd.DataFrame({"jogador": selected_players})
    comparison["passes"] = comparison["jogador"].map(passes.groupby("player_name").size()).fillna(0).astype(int)
    comparison["passes completos"] = comparison["jogador"].map(passes.loc[passes["outcome"].eq("Complete")].groupby("player_name").size()).fillna(0).astype(int)
    comparison["finalizações"] = comparison["jogador"].map(shots.groupby("player_name").size()).fillna(0).astype(int)
    comparison["gols"] = comparison["jogador"].map(shots.loc[shots["outcome"].eq("Goal")].groupby("player_name").size()).fillna(0).astype(int)
    comparison["acerto de passe (%)"] = comparison["passes completos"].div(comparison["passes"]).fillna(0).mul(100).round(1)
    st.dataframe(comparison, use_container_width=True, hide_index=True)


def main():
    st.title("Dashboard de Futebol - StatsBomb")
    with st.container():
        st.subheader("Pergunta de análise")
        st.markdown("**Como passes, finalizações e gols variam entre os jogadores e as equipes desta partida?**")
    progress = st.progress(0, text="Carregando catálogo de competições")
    try:
        competitions = get_competitions()
        progress.progress(35, text="Preparando filtros")
        competition, season_name, match = render_filters(competitions)
        if match is None:
            progress.empty()
            return
        with st.spinner("Carregando e normalizando os eventos da partida..."):
            events_df = get_events(int(match.name))
        progress.progress(100, text="Dados prontos para análise")
        progress.empty()
    except Exception as error:
        progress.empty()
        st.error("Não foi possível consultar os dados abertos da StatsBomb.")
        st.caption(f"Detalhe técnico: {error}")
        return
    if events_df.empty:
        st.warning("A partida selecionada não possui eventos disponíveis.")
        return
    render_dashboard(events_df, match, competition, season_name)


if __name__ == "__main__":
    main()
