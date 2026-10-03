from typing import Optional, List
from datetime import date
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


class Availability(str, Enum):
    AVAILABLE = "available"
    RENTED = "rented"
    UNAVAILABLE = "unavailable"


class Game(SQLModel, table=True):
    __tablename__ = "game"
    gameId: Optional[int] = Field(default=None, primary_key=True)
    title: str
    listings: List["Listing"] = Relationship(back_populates="game")


class Customer(SQLModel, table=True):
    __tablename__ = "customer"
    id: Optional[int] = Field(default=None, primary_key=True)   # inherited from User-style id
    username: str = Field(index=True, unique=True)
    password: str

    payments: List["Payment"] = Relationship(back_populates="customer")
    listings: List["Listing"] = Relationship(back_populates="owner")
    rentals: List["Rental"] = Relationship(back_populates="renter")

    # ----- Methods per Model Diagram -----
    def list_game(self, game: "Game", condition: str, price: float) -> "Listing":
        """Create a Listing owned by this customer for the given game."""
        return Listing(
            gameId=game.gameId,
            ownerId=self.id,
            condition=condition,
            price=price,
            availability=Availability.AVAILABLE,
        )

    def rent_game(self, listing: "Listing") -> "Rental":
        """Create a Rental for this customer from an available listing."""
        if listing.availability != Availability.AVAILABLE:
            raise ValueError(f"Listing {listing.listingId} is not available")
        listing.availability = Availability.RENTED
        return Rental(
            listingId=listing.listingId,
            renterId=self.id,
            rentalDate=date.today(),
        )

    def return_game(self, rental: "Rental", amount: float) -> "Payment":
        """Mark the rental returned and create a Payment."""
        if rental.returnDate is not None:
            raise ValueError(f"Rental {rental.rentalId} already returned")
        rental.returnDate = date.today()
        return Payment(
            rentalId=rental.rentalId,
            customerId=self.id,
            payment_date=date.today(),
            amount=amount,
        )


class Listing(SQLModel, table=True):
    __tablename__ = "listing"
    listingId: Optional[int] = Field(default=None, primary_key=True)
    gameId: int = Field(foreign_key="game.gameId")
    ownerId: int = Field(foreign_key="customer.id")
    condition: str
    availability: Availability = Field(default=Availability.AVAILABLE)
    price: float

    game: Optional[Game] = Relationship(back_populates="listings")
    owner: Optional[Customer] = Relationship(back_populates="listings")
    rentals: List["Rental"] = Relationship(back_populates="listing")


class Rental(SQLModel, table=True):
    __tablename__ = "rental"
    rentalId: Optional[int] = Field(default=None, primary_key=True)
    listingId: int = Field(foreign_key="listing.listingId")
    renterId: int = Field(foreign_key="customer.id")
    rentalDate: date
    returnDate: Optional[date] = None

    listing: Optional[Listing] = Relationship(back_populates="rentals")
    renter: Optional[Customer] = Relationship(back_populates="rentals")
    payments: List["Payment"] = Relationship(back_populates="rental")

    def toJSON(self) -> dict:
        """Per Model Diagram: return dict representation."""
        return {
            "rentalId": self.rentalId,
            "listingId": self.listingId,
            "renterId": self.renterId,
            "rentalDate": str(self.rentalDate),
            "returnDate": str(self.returnDate) if self.returnDate else None,
        }


class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    paymentId: Optional[int] = Field(default=None, primary_key=True)
    rentalId: int = Field(foreign_key="rental.rentalId")
    customerId: int = Field(foreign_key="customer.id")
    payment_date: date
    amount: float

    rental: Optional[Rental] = Relationship(back_populates="payments")
    customer: Optional[Customer] = Relationship(back_populates="payments")

    def toJSON(self) -> dict:
        """Per Model Diagram: return dict representation."""
        return {
            "paymentId": self.paymentId,
            "rentalId": self.rentalId,
            "customerId": self.customerId,
            "payment_date": str(self.payment_date),
            "amount": self.amount,
        }