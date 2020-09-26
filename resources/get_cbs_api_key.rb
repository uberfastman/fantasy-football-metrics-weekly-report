# code snippets taken from https://github.com/geoffharcourt/cbs_fantasy_sports_api_token_fetcher by @geoffharcourt

require "httparty"

league_name_arg = ARGV[0]
userid_arg = ARGV[1]
password_arg = ARGV[2]

class CbsFantasySportsApiTokenFetcher
  TOKEN_REGEX = /(?<=var token = ").+(?=")/
  URL = "https://www.cbssports.com/login".freeze
  VERSION = "0.1.0"

  def initialize(league_name:, user_id:, password:)
    @league_name = league_name
    @user_id = user_id
    @password = password
  end

  def fetch
    page.match(TOKEN_REGEX).to_s
  end

  private

  attr_reader :league_name, :password, :user_id

  def page
    @_page ||= HTTParty.post(
      URL,
      body: { userid: user_id, password: password, xurl: xurl }
    ).body
  end

  def xurl
    "https://#{league_name}.football.cbssports.com/"
  end
end

token = CbsFantasySportsApiTokenFetcher.new(
  league_name: "#{league_name_arg}",
  user_id: "#{userid_arg}",
  password: "#{password_arg}"
).fetch

print token
