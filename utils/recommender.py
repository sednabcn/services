def recommend(campaign_data):
    """
    Analyze response rates and provide simple recommendations.
    """
    sent = campaign_data.get("sent", 0)
    replies = campaign_data.get("replies", 0)
    if sent == 0:
        return "No emails sent yet."
    rate = replies / sent
    if rate < 0.1:
        return "Low response rate, consider improving subject line."
    elif rate > 0.5:
        return "High engagement! Keep current approach."
    else:
        return "Response rate normal."
