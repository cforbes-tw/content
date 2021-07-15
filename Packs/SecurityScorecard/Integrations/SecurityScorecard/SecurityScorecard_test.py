from SecurityScorecard import \
    Client, \
    DATE_FORMAT, \
    is_domain_valid, \
    is_email_valid, \
    is_date_valid, \
    incidents_to_import

import json
import io
import datetime
import pytest  # type: ignore
import re

""" Helper Functions Test Data"""


def load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


domain_test_data = [("google.com", True), ("sometestdomain", False)]
date_test_data = [("2021-12-31", True), ("2021-13-31", False), ("202-12-31", False)]
email_test_data = [("username@domain.com", True), ("username.com", False), ("username@", False)]
alerts_mock = load_json("./test_data/alerts/alerts.json")
portfolios_mock = load_json("./test_data/portfolios/portfolios.json")
companies_mock = load_json("./test_data/portfolios/companies.json")
portfolio_not_found = load_json("./test_data/portfolios/portfolio_not_found.json")
score_mock = load_json("./test_data/companies/score.json")
factor_score_mock = load_json("./test_data/companies/factor_score.json")
historical_score_mock = load_json("./test_data/companies/historical_score.json")
historical_factor_score_mock = load_json("./test_data/companies/historical_factor_score.json")
create_grade_alert_mock = load_json("./test_data/alerts/create_grade_alert.json")
create_score_alert_mock = load_json("./test_data/alerts/create_score_alert.json")

""" Helper Functions Unit Tests"""


@pytest.mark.parametrize("domain,result", domain_test_data)
def test_is_domain_valid(domain, result):
    for domain, result in domain_test_data:
        assert is_domain_valid(domain) == result


@pytest.mark.parametrize("date,result", date_test_data)
def test_is_date_valid(date, result):
    for date, result in date_test_data:
        assert is_date_valid(date) == result


@pytest.mark.parametrize("email,result", email_test_data)
def test_is_email_valid(email, result):
    for email, result in email_test_data:
        assert is_email_valid(email) == result


def test_incidents_to_import(mocker):

    mocker.patch.object(client, "get_alerts_last_week", return_value=alerts_mock)

    response = client.get_alerts_last_week(email="some@email.com")

    assert response.get('entries')

    entries = response.get('entries')

    assert len(entries) == 9

    # 3 day in seconds
    seconds_ago = 3 * 86400

    # Set runtime
    now = int(datetime.datetime(2021, 7, 12).timestamp()) - seconds_ago

    incidents = incidents_to_import(entries)

    assert len(incidents) == 0

    # Iterate over each incident and ensure they
    # were supposed to be imported
    for incident in incidents:
        incident_time = incident["occurred"]
        incident_timestamp = int(datetime.datetime.strptime(incident_time, DATE_FORMAT).timestamp())
        assert incident_timestamp > now


""" TEST CONSTANTS """


USERNAME = "user@domain.com"
PORTFOLIO_ID = "1"
PORTFOLIO_ID_NE = "2"
DOMAIN = "domain1.com"
DOMAIN_NE = "domain2.com"
ALERT_ID = "1"
ALERT_ID_NE = "2"

""" Endpoints """

PORTFOLIO_ROOT_EP = "/portfolios"
PORTFOLIO_FOUND_EP = "{0}/1/companies".format(PORTFOLIO_ROOT_EP)
PORTFOLIO_FOUND_EP = "{0}/2/companies".format(PORTFOLIO_ROOT_EP)

COMPANIES_ROOT_EP = "/companies"
COMPANIES_SCORE_EP = "{0}/{1}".format(COMPANIES_ROOT_EP, DOMAIN)
COMPANIES_FACTOR_SCORE_EP = "{0}/{1}/factors".format(COMPANIES_ROOT_EP, DOMAIN)
COMPANIES_HISTORY_SCORE_EP = "{0}/{1}/history/score".format(COMPANIES_ROOT_EP, DOMAIN)
COMPANIES_HISTORY_FACTOR_SCORE_EP = "{0}/{1}/history/factor/score".format(COMPANIES_ROOT_EP, DOMAIN)
COMPANIES_SERVICES_EP = "{0}/{1}/services".format(COMPANIES_ROOT_EP, DOMAIN)

ALERTS_ROOT_EP = "/users/by-username/{0}/alerts".format(USERNAME)
ALERTS_TYPE_SCORE = "score"
ALERTS_TYPE_GRADE = "grade"
ALERTS_GRADE_EP = "{0}/grade".format(ALERTS_ROOT_EP)
ALERTS_SCORE_EP = "{0}/score".format(ALERTS_ROOT_EP)
ALERTS_DELETE_SCORE_EP = "{0}/{1}/{2}".format(ALERTS_ROOT_EP, ALERTS_TYPE_SCORE, ALERT_ID)
ALERTS_DELETE_GRADE_EP = "{0}/{1}/{2}".format(ALERTS_ROOT_EP, ALERTS_TYPE_GRADE, ALERT_ID)
NOTIFICATIONS_ROOT_EP = "/users/by-username/{0}/notifications/recent".format(USERNAME)


""" Client Unit Tests """


MOCK_URL = "mock://securityscorecard-mock-url"

client = Client(
    base_url=MOCK_URL,
    verify=False,
    proxy=False
)


def test_portfolios_list(mocker):

    mocker.patch.object(client, "get_portfolios", return_value=portfolios_mock)

    response = client.get_portfolios()

    assert response == portfolios_mock


def test_portfolio_list_companies(mocker):

    """
        Checks cases where the portfolio exists and doesn't exist
    """

    # 1. Exiting Portfolio
    mocker.patch.object(client, "get_companies_in_portfolio", return_value=companies_mock)
    response_portfolio = client.get_companies_in_portfolio(PORTFOLIO_ID)

    assert response_portfolio.get("entries")

    companies = response_portfolio.get("entries")

    assert len(companies) == 3

    # 2. Portfolio doesn't exist
    mocker.patch.object(client, "get_companies_in_portfolio", return_value=portfolio_not_found)
    portfolio_not_exist_response = client.get_companies_in_portfolio(PORTFOLIO_ID_NE)

    assert portfolio_not_exist_response["error"]["message"] == "portfolio not found"


def test_get_company_score(mocker):

    mocker.patch.object(client, "get_company_score", return_value=score_mock)

    response_score = client.get_company_score(domain=DOMAIN)

    assert response_score == score_mock
    assert response_score["domain"] == DOMAIN
    assert isinstance(response_score["score"], int)
    assert isinstance(response_score["last30day_score_change"], int)
    assert re.match("[A-F]", response_score["grade"])


def test_get_company_factor_score(mocker):

    mocker.patch.object(client, "get_company_factor_score", return_value=factor_score_mock)

    response_factor_score = client.get_company_factor_score(domain=DOMAIN)

    assert response_factor_score == factor_score_mock

    assert response_factor_score["total"] == len(response_factor_score["entries"])

    sample_factor = response_factor_score["entries"][0]

    assert isinstance(sample_factor["score"], int)
    assert re.match("[A-F]", sample_factor["grade"])


def test_get_company_historical_scores(mocker):

    mocker.patch.object(client, "get_company_historical_scores", return_value=historical_score_mock)

    response_historical_score = client.get_company_historical_scores(
        domain=DOMAIN,
        _from="2021-07-01",
        to="2021-07-08",
        timing="daily"
    )

    assert response_historical_score == historical_score_mock
    assert len(response_historical_score["entries"]) == 8
    assert isinstance(response_historical_score["entries"][0]["score"], int)
    assert is_domain_valid(response_historical_score["entries"][0]["domain"])


def test_get_company_historical_factor_scores(mocker):

    mocker.patch.object(client, "get_company_historical_factor_scores", return_value=historical_factor_score_mock)

    response_historical_factor_score = client.get_company_historical_factor_scores(
        domain=DOMAIN,
        _from="2021-07-01",
        to="2021-07-08",
        timing="daily"
    )

    assert response_historical_factor_score == historical_factor_score_mock
    assert len(response_historical_factor_score["entries"]) == 8
    assert len(response_historical_factor_score["entries"][0]["factors"]) == 10
    assert isinstance(response_historical_factor_score["entries"][0]["factors"][0]["score"], int)


def test_create_grade_change_alert(mocker):

    mocker.patch.object(client, "create_grade_change_alert", return_value=create_grade_alert_mock)

    response = client.create_grade_change_alert(
        email=USERNAME,
        change_direction="drops",
        score_types="application_security",
        target="any_followed_company"
    )

    assert response == create_grade_alert_mock


def test_create_score_threshold_alert(mocker):

    mocker.patch.object(client, "create_score_threshold_alert", return_value=create_score_alert_mock)

    response = client.create_score_threshold_alert(
        email=USERNAME,
        change_direction="drops_below",
        threshold=70,
        score_types="application_security",
        target="any_followed_company"
    )

    assert response == create_score_alert_mock


def test_get_alerts_last_week(mocker):

    mocker.patch.object(client, "get_alerts_last_week", return_value=alerts_mock)

    response = client.get_alerts_last_week(email=USERNAME)

    assert response == alerts_mock
    assert response["size"] == 9
    assert is_domain_valid(response["entries"][0]["domain"])
    assert isinstance(response["entries"][0]["my_scorecard"], bool)



def test_get_domain_services(mocker):
    pass


def test_fetch_alerts(mocker):
    pass


def test_test_module(mocker):
    pass


def main() -> None:
    pass


if __name__ == "builtins":
    main()
