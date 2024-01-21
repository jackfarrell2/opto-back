from pytz import timezone

def format_slate(slate):
    est_version = slate.date.astimezone(timezone("America/New_York"))
    time = est_version.strftime("%m/%d, %I:%M%p")
    return f"{time} ({slate.game_count} games)"