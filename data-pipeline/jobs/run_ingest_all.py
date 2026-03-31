from ingestors import reddit_ingestor, steam_ingestor, youtube_ingestor


def run() -> None:
    steam_ingestor.run()
    youtube_ingestor.run()
    reddit_ingestor.run()


if __name__ == "__main__":
    run()
