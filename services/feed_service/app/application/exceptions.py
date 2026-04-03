class FeedError(Exception):
    pass


class VideoNotFoundError(FeedError):
    pass


class InvalidFollowError(FeedError):
    pass
