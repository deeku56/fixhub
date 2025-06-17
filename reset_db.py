from app import db, Issue, Upvote, app

if __name__ == "__main__":
    print("⚠️  Deleting all upvotes and issues...")

    try:
        with app.app_context():
            Upvote.query.delete()
            Issue.query.delete()
            db.session.commit()
            print("✅ All issues and upvotes have been cleared!")
    except Exception as e:
        print(f"❌ Error while resetting: {e}")
