__author__ = "Wren J. R. (uberfastman)"
__email__ = "wrenjr@yahoo.com"


def user_week_input_validation(config, week, retrieved_current_week):
    # user input validation
    if week:
        week_for_report = week
    else:
        week_for_report = config.get("Configuration", "week_for_report")
    try:
        current_week = retrieved_current_week
        if week_for_report == "default":
            if (int(current_week) - 1) > 0:
                week_for_report = str(int(current_week) - 1)
            else:
                first_week_incomplete = input(
                    "The first week of the season is not yet complete. "
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if first_week_incomplete == "y":
                    week_for_report = current_week
                elif first_week_incomplete == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")

        elif 0 < int(week_for_report) < 18:
            if 0 < int(week_for_report) <= int(current_week) - 1:
                week_for_report = week_for_report
            else:
                incomplete_week = input(
                    "Are you sure you want to generate a report for an incomplete week? (y/n) -> ")
                if incomplete_week == "y":
                    week_for_report = week_for_report
                elif incomplete_week == "n":
                    raise ValueError("It is recommended that you NOT generate a report for an incomplete week.")
                else:
                    raise ValueError("Please only select 'y' or 'n'. Try running the report generator again.")
        else:
            raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")
    except ValueError:
        raise ValueError("You must select either 'default' or an integer from 1 to 17 for the chosen week.")

    return week_for_report
