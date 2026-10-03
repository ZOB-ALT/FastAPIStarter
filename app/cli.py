import typer
from datetime import date
from sqlmodel import select
from app.database import create_db_and_tables, drop_all, get_cli_session
from app.models import (
    Customer, Game, Listing, Rental, Payment, Availability,
)

cli = typer.Typer()


# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------
@cli.command()
def initialize():
    """Drop all tables, recreate them, and load sample data."""
    with get_cli_session() as db:
        drop_all()
        create_db_and_tables()

        john = Customer(username="john", password="johnpass")
        jane = Customer(username="jane", password="janepass")
        db.add(john); db.add(jane); db.commit()
        db.refresh(john); db.refresh(jane)

        zelda = Game(title="Zelda")
        mario = Game(title="Mario Kart")
        db.add(zelda); db.add(mario); db.commit()
        db.refresh(zelda); db.refresh(mario)

        l1 = Listing(gameId=zelda.gameId, ownerId=john.id,
                     condition="Good", price=20.0)
        l2 = Listing(gameId=mario.gameId, ownerId=jane.id,
                     condition="Excellent", price=15.0)
        db.add(l1); db.add(l2); db.commit()
        print("Database initialized with sample data.")


# ------------------------------------------------------------------
# 1. View Game Catalogue (Customer)
# ------------------------------------------------------------------
@cli.command()
def view_catalogue():
    """View all available games with prices (Customer)."""
    with get_cli_session() as db:
        listings = db.exec(
            select(Listing).where(Listing.availability == Availability.AVAILABLE)
        ).all()
        if not listings:
            print("No games currently available.")
            return
        print("=" * 60)
        print("GAME CATALOGUE")
        print("=" * 60)
        for l in listings:
            game = db.get(Game, l.gameId)
            owner = db.get(Customer, l.ownerId)
            print(f"  Listing ID : {l.listingId}")
            print(f"  Game       : {game.title}")
            print(f"  Condition  : {l.condition}")
            print(f"  Price      : ${l.price}")
            print(f"  Owner      : {owner.username}")
            print("-" * 60)


# ------------------------------------------------------------------
# 2. List Game with Price (Customer)
# ------------------------------------------------------------------
@cli.command()
def list_game(
    username: str = typer.Argument(..., help="Username of the listing owner"),
    game_title: str = typer.Argument(..., help="Title of the game to list"),
    condition: str = typer.Argument(..., help="Condition of the game copy"),
    price: float = typer.Argument(..., help="Rental price"),
):
    """Customer lists a copy of a game they own for rental."""
    with get_cli_session() as db:
        customer = db.exec(
            select(Customer).where(Customer.username == username)
        ).first()
        if not customer:
            print(f"Customer '{username}' not found.")
            return

        game = db.exec(select(Game).where(Game.title == game_title)).first()
        if not game:
            game = Game(title=game_title)
            db.add(game); db.commit(); db.refresh(game)

        # Uses the Customer.list_game() model method per the diagram
        listing = customer.list_game(game, condition, price)
        db.add(listing); db.commit(); db.refresh(listing)
        print(f"'{game_title}' listed by {username} "
              f"(Listing ID={listing.listingId}) at ${price}.")


# ------------------------------------------------------------------
# 3. Rent Game (Customer)
# ------------------------------------------------------------------
@cli.command()
def rent_game(
    username: str = typer.Argument(..., help="Username of the renter"),
    listing_id: int = typer.Argument(..., help="Listing ID to rent"),
):
    """Customer rents a game."""
    with get_cli_session() as db:
        customer = db.exec(
            select(Customer).where(Customer.username == username)
        ).first()
        if not customer:
            print(f"Customer '{username}' not found.")
            return

        listing = db.get(Listing, listing_id)
        if not listing:
            print(f"Listing {listing_id} not found.")
            return

        try:
            # Uses the Customer.rent_game() model method per the diagram
            rental = customer.rent_game(listing)
        except ValueError as e:
            print(e)
            return

        db.add(listing); db.add(rental); db.commit(); db.refresh(rental)
        print(f"{username} rented listing {listing_id}. "
              f"Rental ID={rental.rentalId}, date={rental.rentalDate}.")


# ------------------------------------------------------------------
# 4. Return Game with Payment (Customer)
# ------------------------------------------------------------------
@cli.command()
def return_game(
    username: str = typer.Argument(..., help="Username of the renter"),
    rental_id: int = typer.Argument(..., help="Rental ID being returned"),
    amount: float = typer.Argument(..., help="Payment amount"),
):
    """Customer returns a game and makes a payment."""
    with get_cli_session() as db:
        customer = db.exec(
            select(Customer).where(Customer.username == username)
        ).first()
        if not customer:
            print(f"Customer '{username}' not found.")
            return

        rental = db.get(Rental, rental_id)
        if not rental:
            print(f"Rental {rental_id} not found.")
            return

        # Business rule: late fee (7-day window)
        days_rented = (date.today() - rental.rentalDate).days
        late_fee = max(0, days_rented - 7) * 5.0
        if late_fee:
            print(f"Late return! {days_rented - 7} day(s) late -> fee ${late_fee:.2f}")

        total = amount + late_fee

        try:
            # Uses the Customer.return_game() model method per the diagram
            payment = customer.return_game(rental, total)
        except ValueError as e:
            print(e)
            return

        # Also free up the listing
        listing = db.get(Listing, rental.listingId)
        listing.availability = Availability.AVAILABLE

        db.add(rental); db.add(listing); db.add(payment)
        db.commit(); db.refresh(payment)
        print(f"Rental {rental_id} returned by {username}. "
              f"Payment ID={payment.paymentId}, amount=${total:.2f}.")


if __name__ == "__main__":
    cli()