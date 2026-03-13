from src.state.session_state import Page, SessionStateManager
from src.views.home_view import HomeView


class HomePresenter:
    def __init__(self, view: HomeView):
        self.view = view

    def present(self) -> None:
        result = self.view.render()
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
