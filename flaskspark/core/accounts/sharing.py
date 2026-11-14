"""An account as an item to share (flaskspark.core.shares, type "account"): its owner shares it with roles, read or
write. What a share gives is the modules' business: a module reads the accounts shared with a user with
accounts.for_module(<module>).for_user(user_id, <type>, shared=True) (permission "read" or "write"). Shared means
usable at once (no joining). Named in the core's manifest (Core.SHAREABLES).

A change of its shares is an account change «shared» (accounts.AccountChange): the modules may veto it before
(Module.account_change_veto) and are told after it is committed (accounts.listen, the event «accounts»)."""

from __future__ import annotations

from ..module import N_
from ..shares import Shareable, ShareError

SHARE_TYPE = "account"


class AccountShareable(Shareable):
    TYPE, JOINS, LABEL = SHARE_TYPE, False, N_("Account")

    def owner_of(self, s, object_id: int) -> int | None:
        from ..models import Account

        account = s.get(Account, object_id)
        return account.user_id if account is not None else None

    def name_of(self, s, object_id: int) -> str:
        from ..models import Account

        account = s.get(Account, object_id)
        return account.name if account is not None else "?"

    def _types(self, s, object_id: int) -> tuple[str, ...]:
        from .store import type_rows

        return tuple(type_rows(s, object_id))

    def check_change(self, s, object_id: int, owner_id: int, wanted: dict[int, str]) -> None:
        from . import AccountChange, AccountError, veto

        try:
            veto(AccountChange("shared", object_id, owner_id, self._types(s, object_id)))
        except AccountError as error:
            raise ShareError(error.template, **error.params) from None

    def shares_changed(self, object_id: int, owner_id: int, concerned: set[int]) -> None:
        from .. import db
        from . import AccountChange, changed

        with db.session() as s:
            keys = self._types(s, object_id)
        changed(AccountChange("shared", object_id, owner_id, keys), concerned - {owner_id})
