from sqlmodel import SQLModel, Field


class Camera(SQLModel, table=True):
    ip: str = Field(primary_key=True)
    username: str
    password: str


    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other
