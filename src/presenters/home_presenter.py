from src.state.session_state import Page, SessionStateManager
from src.views.home_view import HomeView


class HomePresenter:
    def __init__(self, view: HomeView):
        self.view = view

    def present(self, is_admin: bool, pending_count: int) -> None:
        result = self.view.render(is_admin=is_admin, pending_count=pending_count)
        if result.open_approval:
            SessionStateManager.go(Page.APPROVAL)
        if result.open_locker:
            SessionStateManager.go(Page.LOCKER)
        if result.open_compressor:
            SessionStateManager.go(Page.COMPRESSOR)
        if result.open_converter:
            SessionStateManager.go(Page.CONVERTER)
        if result.open_watermark:
            SessionStateManager.go(Page.WATERMARK)
        if result.open_split_merge:
            SessionStateManager.go(Page.SPLIT_MERGE)
