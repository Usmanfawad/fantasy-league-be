from sqlmodel import Session


class UserService:
    """
    Deprecated shim. The legacy `User` model and routes were removed.
    Use manager-focused services instead:
      - Authentication and account creation: `app.auth.service.AuthService`
      - Manager domain operations: `app.manager.service.ManagerService`
    """

    def __init__(self, session: Session):
        self.session = session

    def __getattr__(self, _name):  # pragma: no cover
        raise RuntimeError(
            "UserService is deprecated. Use AuthService and ManagerService instead."
        )

