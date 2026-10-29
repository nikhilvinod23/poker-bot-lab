"""Launch the hotseat desktop game, or use --cli for the terminal version."""
import sys
from .engine import Game


def cli():
    game = Game()
    while True:
        if game.done:
            print(game.result, "Stacks:", game.stacks)
            if game.showdown:
                print("Hands:", game.hole)
            if min(game.stacks) == 0 or input("Next hand? [y/N] ").lower() != "y":
                break
            game = Game(game.stacks, 1 - game.dealer)
        input(f"Pass to Player {game.current + 1}. Press Enter to reveal.")
        obs = game.observation(game.current)
        print("Board:", obs["board"], "Your cards:", obs["hole_cards"])
        print("Stacks:", obs["stacks"], "Pot:", obs["pot"], "To call:", obs["to_call"])
        while True:
            choice = input(" / ".join(obs["legal_actions"]) + ": ").strip().lower()
            if choice in obs["legal_actions"]:
                break
        game.step(choice)
        print("\n" * 40)


def desktop():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title("Hold'em Lab • Two-player table")
    root.geometry("760x650")
    root.minsize(640, 580)
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)
    game = Game()
    title = ttk.Label(frame, font=("Segoe UI", 22, "bold"))
    title.pack(anchor="w")
    ttk.Label(frame, text="Fixed limit • 1 / 2 blinds • Human vs human • Pass-and-play").pack(anchor="w", pady=8)
    status = ttk.Label(frame, font=("Segoe UI", 12))
    status.pack(anchor="w", pady=8)
    board = ttk.Label(frame, font=("Consolas", 23))
    board.pack(anchor="w", pady=16)
    private = ttk.Label(frame, font=("Consolas", 17))
    private.pack(anchor="w", pady=12)
    message = ttk.Label(frame, wraplength=650)
    message.pack(anchor="w", pady=10)
    controls = ttk.Frame(frame)
    controls.pack(anchor="w", pady=12)
    log = tk.Text(frame, height=10, wrap="word", font=("Segoe UI", 10))
    log.pack(fill="both", expand=True)

    def cards(items):
        suits = {"c": "♣", "d": "♦", "h": "♥", "s": "♠"}
        return "  ".join(c[0] + suits[c[1]] for c in items) or "—"

    def render(reveal=False):
        for child in controls.winfo_children():
            child.destroy()
        title.config(text="Hand complete" if game.done else f"Player {game.current + 1}'s turn")
        status.config(text=f"Player 1: {game.stacks[0]} chips    Player 2: {game.stacks[1]} chips    Pot: {game.pot}")
        board.config(text="Board: " + cards(game.board))
        private.config(text="Cards hidden — pass the device")
        if game.done:
            message.config(text=game.result)
            if game.showdown:
                private.config(text=f"P1: {cards(game.hole[0])}     P2: {cards(game.hole[1])}")
            ttk.Button(controls, text="Next hand", command=next_hand, state="normal" if min(game.stacks) else "disabled").pack(side="left", padx=4)
            ttk.Button(controls, text="New session", command=new_session).pack(side="left", padx=4)
        elif reveal:
            obs = game.observation(game.current)
            private.config(text="Your cards: " + cards(obs["hole_cards"]))
            message.config(text=f"{('Preflop','Flop','Turn','River')[game.street]} • To call: {obs['to_call']} • Raise increment: {2 if game.street < 2 else 4}")
            for action in obs["legal_actions"]:
                ttk.Button(controls, text="Bet / Raise" if action == "raise" else action.title(), command=lambda a=action: act(a)).pack(side="left", padx=4)
        else:
            message.config(text="Only the current player should reveal their cards. You can control both seats to explore the rules.")
            ttk.Button(controls, text="Reveal my cards", command=lambda: render(True)).pack(side="left")
        log.config(state="normal")
        log.delete("1.0", "end")
        log.insert("1.0", "\n".join(game.history))
        log.config(state="disabled")
        log.see("end")

    def act(action):
        game.step(action)
        render()

    def next_hand():
        nonlocal game
        game = Game(game.stacks, 1 - game.dealer)
        render()

    def new_session():
        nonlocal game
        game = Game()
        render()

    render()
    root.mainloop()


if __name__ == "__main__":
    cli() if "--cli" in sys.argv else desktop()
