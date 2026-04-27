import streamlit as st
import random
import os
import base64
from io import BytesIO
from PIL import Image, ImageEnhance
from treys import Card, Evaluator, Deck
from st_clickable_images import clickable_images

st.set_page_config(page_title="Poker Odds Calculator", layout="wide")

RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]

RANK_MAP = {
    "A": "Ace",
    "K": "King",
    "Q": "Queen",
    "J": "Jack",
    "T": "10",
    "9": "9",
    "8": "8",
    "7": "7",
    "6": "6",
    "5": "5",
    "4": "4",
    "3": "3",
    "2": "2",
}

SUIT_MAP = {
    "h": "heart",
    "d": "diamond",
    "c": "club",
    "s": "spade",
}

MAX_PLAYERS = 10
PLAYERS_PER_ROW = 5
SIMULATIONS = 10000

GRID_CARD_HEIGHT = "72px"
PLAYER_CARD_HEIGHT = "115px"
BOARD_CARD_HEIGHT = "105px"

st.title("Poker Odds Calculator")


def get_card_image(card_code):
    rank = RANK_MAP[card_code[0]]
    suit = SUIT_MAP[card_code[1]]
    return f"cards/{suit}{rank}.png"


def get_card_back_image():
    if os.path.exists("cards/redBack.png"):
        return "cards/redBack.png"
    return "cards/blueBack.png"


def image_to_data_url(path):
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/png;base64,{encoded}"


def dimmed_image_to_data_url(path):
    image = Image.open(path).convert("RGBA")
    image = ImageEnhance.Brightness(image).enhance(0.35)
    image = ImageEnhance.Color(image).enhance(0.35)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{encoded}"


def parse_cards(card_codes):
    return [Card.new(card) for card in card_codes]


def face_up_cards(cards):
    return [card for card in cards if card is not None]


@st.cache_data
def cached_multi_player_simulation(players_tuple, board_tuple, simulations):
    evaluator = Evaluator()
    player_count = len(players_tuple)
    equity = [0.0 for _ in range(player_count)]

    known_board_codes = [card for card in board_tuple if card]
    known_board = parse_cards(known_board_codes)

    for _ in range(simulations):
        deck = Deck()

        completed_players = []
        used_cards = known_board.copy()

        for player_cards_tuple in players_tuple:
            known_codes = [card for card in player_cards_tuple if card]
            known_cards = parse_cards(known_codes)
            completed_players.append(known_cards)
            used_cards.extend(known_cards)

        deck.cards = [card for card in deck.cards if card not in used_cards]

        for i in range(player_count):
            missing_cards = 2 - len(completed_players[i])

            if missing_cards > 0:
                sampled_cards = random.sample(deck.cards, missing_cards)
                completed_players[i].extend(sampled_cards)
                deck.cards = [card for card in deck.cards if card not in sampled_cards]

        missing_board_cards = 5 - len(known_board)
        sampled_board = random.sample(deck.cards, missing_board_cards)
        board = known_board + sampled_board

        scores = [
            evaluator.evaluate(board, completed_players[i])
            for i in range(player_count)
        ]

        best_score = min(scores)
        winners = [i for i, score in enumerate(scores) if score == best_score]
        split_equity = 1 / len(winners)

        for winner in winners:
            equity[winner] += split_equity

    return equity


if "players" not in st.session_state:
    st.session_state.players = [
        {"name": "Player 1", "cards": [None, None]},
        {"name": "Player 2", "cards": [None, None]},
    ]

if "board_cards" not in st.session_state:
    st.session_state.board_cards = [None, None, None, None, None]

if "active_area" not in st.session_state:
    st.session_state.active_area = "player"

if "active_player_index" not in st.session_state:
    st.session_state.active_player_index = 0

if "active_slot" not in st.session_state:
    st.session_state.active_slot = 0

if "show_card_selector" not in st.session_state:
    st.session_state.show_card_selector = False

if "grid_version" not in st.session_state:
    st.session_state.grid_version = 0

if "player_versions" not in st.session_state:
    st.session_state.player_versions = [0 for _ in st.session_state.players]

if len(st.session_state.player_versions) != len(st.session_state.players):
    st.session_state.player_versions = [0 for _ in st.session_state.players]

if "board_version" not in st.session_state:
    st.session_state.board_version = 0


def get_active_cards():
    if st.session_state.active_area == "board":
        return st.session_state.board_cards

    return st.session_state.players[st.session_state.active_player_index]["cards"]


def get_all_used_cards():
    used_cards = []

    for player in st.session_state.players:
        used_cards.extend(face_up_cards(player["cards"]))

    used_cards.extend(face_up_cards(st.session_state.board_cards))

    return used_cards


def get_area_name():
    if st.session_state.active_area == "board":
        return "board"

    return st.session_state.players[st.session_state.active_player_index]["name"].lower()


def renumber_players():
    for i in range(len(st.session_state.players)):
        st.session_state.players[i]["name"] = f"Player {i + 1}"


def select_card(card_code):
    active_cards = get_active_cards()
    used_cards = get_all_used_cards()
    slot = st.session_state.active_slot

    if card_code in used_cards:
        return

    active_cards[slot] = card_code

    if st.session_state.active_area == "player":
        if slot == 0 and active_cards[1] is None:
            st.session_state.active_slot = 1

        if active_cards[0] and active_cards[1]:
            st.session_state.show_card_selector = False
        else:
            st.session_state.show_card_selector = True

    else:
        empty_slots = [i for i, card in enumerate(active_cards) if card is None]

        if empty_slots:
            st.session_state.active_slot = empty_slots[0]
            st.session_state.show_card_selector = True
        else:
            st.session_state.show_card_selector = False


def reset_cards():
    st.session_state.players = [
        {"name": "Player 1", "cards": [None, None]},
        {"name": "Player 2", "cards": [None, None]},
    ]
    st.session_state.board_cards = [None, None, None, None, None]
    st.session_state.active_area = "player"
    st.session_state.active_player_index = 0
    st.session_state.active_slot = 0
    st.session_state.show_card_selector = False
    st.session_state.grid_version += 1
    st.session_state.player_versions = [0 for _ in st.session_state.players]
    st.session_state.board_version += 1


def reset_board():
    st.session_state.board_cards = [None, None, None, None, None]
    st.session_state.board_version += 1

    if st.session_state.active_area == "board":
        st.session_state.active_slot = 0
        st.session_state.show_card_selector = False


def add_player():
    current_players = len(st.session_state.players)

    if current_players < MAX_PLAYERS:
        player_number = current_players + 1
        st.session_state.players.append(
            {"name": f"Player {player_number}", "cards": [None, None]}
        )
        st.session_state.player_versions.append(0)


def remove_player(player_index):
    if player_index <= 1:
        return

    st.session_state.players.pop(player_index)
    st.session_state.player_versions.pop(player_index)
    renumber_players()

    if st.session_state.active_area == "player":
        if st.session_state.active_player_index == player_index:
            st.session_state.active_player_index = 0
            st.session_state.active_slot = 0
            st.session_state.show_card_selector = False
        elif st.session_state.active_player_index > player_index:
            st.session_state.active_player_index -= 1

    st.session_state.grid_version += 1


def handle_player_click(player_index, slot_index):
    cards = st.session_state.players[player_index]["cards"]

    st.session_state.active_area = "player"
    st.session_state.active_player_index = player_index
    st.session_state.active_slot = slot_index

    if cards[slot_index] is not None:
        cards[slot_index] = None
        st.session_state.show_card_selector = False
    else:
        st.session_state.show_card_selector = True

    st.session_state.player_versions[player_index] += 1


def handle_board_click(slot_index):
    st.session_state.active_area = "board"
    st.session_state.active_slot = slot_index

    if st.session_state.board_cards[slot_index] is not None:
        st.session_state.board_cards[slot_index] = None
        st.session_state.show_card_selector = False
    else:
        st.session_state.show_card_selector = True

    st.session_state.board_version += 1


def get_player_equities(simulations):
    players_tuple = tuple(
        tuple(card if card is not None else "" for card in player["cards"])
        for player in st.session_state.players
    )

    board_tuple = tuple(
        card if card is not None else ""
        for card in st.session_state.board_cards
    )

    equity = cached_multi_player_simulation(
        players_tuple,
        board_tuple,
        simulations,
    )

    display_equity = equity.copy()

    unknown_player_indexes = [
        i
        for i, player in enumerate(st.session_state.players)
        if player["cards"][0] is None and player["cards"][1] is None
    ]

    if unknown_player_indexes:
        average_unknown_equity = sum(
            equity[i] for i in unknown_player_indexes
        ) / len(unknown_player_indexes)

        for i in unknown_player_indexes:
            display_equity[i] = average_unknown_equity

    return [f"{value / simulations * 100:.2f}%" for value in display_equity]


def render_player(player_index, odds_value=None):
    player = st.session_state.players[player_index]
    cards = player["cards"]

    images = []
    titles = []

    for i in range(2):
        if cards[i] is None:
            images.append(image_to_data_url(get_card_back_image()))
            titles.append("Face down")
        else:
            images.append(image_to_data_url(get_card_image(cards[i])))
            titles.append(cards[i])

    with st.container(border=True):
        title_col, close_col = st.columns([8, 1])

        with title_col:
            st.subheader(player["name"])

        with close_col:
            if player_index > 1:
                if st.button(
                    "✖",
                    key=f"remove_player_{player_index}",
                    use_container_width=True,
                ):
                    remove_player(player_index)
                    st.rerun()

        clicked = clickable_images(
            images,
            titles=titles,
            div_style={
                "display": "flex",
                "justify-content": "space-around",
            },
            img_style={
                "height": PLAYER_CARD_HEIGHT,
            },
            key=f"player_{player_index}_{st.session_state.player_versions[player_index]}",
        )

        if clicked > -1:
            handle_player_click(player_index, clicked)
            st.rerun()

        if odds_value:
            st.markdown(f"## {odds_value}")


def render_add_player_box():
    with st.container(border=True):
        st.subheader("Add player")
        st.write("")

        if len(st.session_state.players) < MAX_PLAYERS:
            if st.button("＋", use_container_width=True):
                add_player()
                st.rerun()
        else:
            st.info("Maximum 10 players")


def render_players(player_equities):
    total_items = len(st.session_state.players)

    if len(st.session_state.players) < MAX_PLAYERS:
        total_items += 1

    for start in range(0, total_items, PLAYERS_PER_ROW):
        row_items = list(range(start, min(start + PLAYERS_PER_ROW, total_items)))
        cols = st.columns(PLAYERS_PER_ROW)

        for col_index in range(PLAYERS_PER_ROW):
            with cols[col_index]:
                if col_index < len(row_items):
                    item_index = row_items[col_index]

                    if item_index < len(st.session_state.players):
                        odds_value = None

                        if player_equities:
                            odds_value = player_equities[item_index]

                        render_player(item_index, odds_value)
                    else:
                        render_add_player_box()


def render_board():
    images = []
    titles = []

    for i in range(5):
        card = st.session_state.board_cards[i]

        if card is None:
            images.append(image_to_data_url(get_card_back_image()))
            titles.append("Face down")
        else:
            images.append(image_to_data_url(get_card_image(card)))
            titles.append(card)

    with st.container(border=True):
        title_col, close_col = st.columns([8, 1])

        with title_col:
            st.subheader("Board")

        with close_col:
            if st.button("✖", key="reset_board", use_container_width=True):
                reset_board()
                st.rerun()

        clicked = clickable_images(
            images,
            titles=titles,
            div_style={
                "display": "flex",
                "justify-content": "center",
                "gap": "18px",
            },
            img_style={
                "height": BOARD_CARD_HEIGHT,
            },
            key=f"board_{st.session_state.board_version}",
        )

        if clicked > -1:
            handle_board_click(clicked)
            st.rerun()


def render_card_selector():
    with st.container(border=True):
        header_left, header_right = st.columns([8, 1])

        with header_left:
            st.subheader(f"Choose a card for {get_area_name()}")

        with header_right:
            if st.button("✖", key="close_selector", use_container_width=True):
                st.session_state.show_card_selector = False
                st.rerun()

        used_cards = get_all_used_cards()

        for suit in ["h", "d", "c", "s"]:
            card_images = []
            card_codes = []

            for rank in RANKS:
                code = rank + suit
                path = get_card_image(code)

                if os.path.exists(path):
                    if code in used_cards:
                        card_images.append(dimmed_image_to_data_url(path))
                    else:
                        card_images.append(image_to_data_url(path))

                    card_codes.append(code)

            clicked = clickable_images(
                card_images,
                titles=card_codes,
                div_style={
                    "display": "flex",
                    "justify-content": "center",
                    "gap": "6px",
                    "margin-bottom": "8px",
                    "flex-wrap": "nowrap",
                },
                img_style={
                    "height": GRID_CARD_HEIGHT,
                    "width": "auto",
                    "border-radius": "4px",
                    "cursor": "pointer",
                },
                key=f"grid_{suit}_{st.session_state.grid_version}",
            )

            if clicked > -1:
                select_card(card_codes[clicked])
                st.session_state.grid_version += 1
                st.rerun()


top_left, top_right = st.columns([4, 1])

with top_right:
    if st.button("Reset", use_container_width=True):
        reset_cards()
        st.rerun()


simulations = SIMULATIONS

player_equities = get_player_equities(simulations)

render_players(player_equities)

if st.session_state.show_card_selector:
    render_card_selector()

render_board()

if not st.session_state.show_card_selector:
    st.info("Click a face-down card to choose a card.")