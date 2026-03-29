#include "api/api_client.h"
#include "api/api_track.h"
#include "nlohmann/json.hpp"
#include <curl/curl.h>
#include <curl/easy.h>
#include <format>
#include <iostream>
#include <stdexcept>

namespace {
size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp)
{
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

} // namespace

using json = nlohmann::json;

namespace api {

Curl_headers_get::Curl_headers_get(CURL* curl, const std::string& token, const std::string& url):
    curl(curl)
{
    headers = curl_slist_append(headers, std::format("Authorization: OAuth {}", token).c_str());
    headers = curl_slist_append(headers, "User-Agent: MyYandexMusicApp/1.0");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &responce);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
}

Curl_headers_get::Curl_headers_get(Curl_headers_get&& other) noexcept:
    headers(other.headers), responce(std::move(other.responce)), curl(other.curl)
{
    other.headers = nullptr;
}
Curl_headers_get& Curl_headers_get::operator=(Curl_headers_get&& other) noexcept
{
    headers = other.headers;
    responce = std::move(other.responce);
    curl = other.curl;
    other.headers = nullptr;
    return *this;
}
Curl_headers_get::~Curl_headers_get()
{
    if (headers != nullptr)
        curl_slist_free_all(headers);
}

bool Curl_headers_get::perform() const
{
    const auto res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        std::cout << std::format("CURL error: {}\n", curl_easy_strerror(res));
        return false;
    }

    long response_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

    if (response_code != 200) {
        std::cout << std::format("Error {}, Response: {}\n", response_code, responce);
        return false;
    }
    return true;
}

/// -------------------------------------------------------------------------------------- ///
Curl_headers_download::Curl_headers_download(CURL* curl, const std::string& token, const std::string& url):
    curl(curl)
{
    headers = curl_slist_append(headers, std::format("Authorization: OAuth {}", token).c_str());
    headers = curl_slist_append(headers, "User-Agent: MyYandexMusicApp/1.0");
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &responce);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
}

Curl_headers_download::~Curl_headers_download()
{
    if (headers != nullptr)
        curl_slist_free_all(headers);
}

bool Curl_headers_download::perform() const
{
    const auto res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        std::cout << std::format("CURL error: {}\n", curl_easy_strerror(res));
        return false;
    }

    long response_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

    if (response_code != 200) {
        std::cout << std::format("Error {}, Response: {}\n", response_code, responce);
        return false;
    }
    return true;
}

Account::Account(const std::string& json_str)
{
    auto responce = json::parse(json_str)["result"]["account"];
    uid = responce["uid"];
    first_name = responce["firstName"];
    second_name = responce["secondName"];
    display_name = responce["displayName"];
}

Client::Client(std::string token): curl(curl_easy_init()), token(std::move(token))
{
    if (!curl)
        throw std::runtime_error("Failed to initialize CURL");
    receive_account_info();
}

Client::~Client()
{
    curl_easy_cleanup(curl);
}

void Client::receive_account_info()
{
    const auto url = std::format("{}/account/status", host);
    Curl_headers_get headers { curl, token, url };

    if (!headers.perform())
        return;

    account = Account { headers.responce };
    std::cout << std::format("Account {} with name {}\n", account.uid, account.display_name);
}

std::vector<Track> Client::liked_tracks()
{
    const auto url = std::format("{}/users/{}/likes/tracks", host, account.uid);
    Curl_headers_get headers { curl, token, url };

    if (!headers.perform())
        return {};

    std::vector<Track> tracks;
    auto json = json::parse(headers.responce)["result"]["library"];
    for (const auto& object : json["tracks"])
        tracks.emplace_back(this, object["id"]);
    return tracks;
}

void Client::playlists()
{
    const auto url = std::format("{}/users/{}/playlists/list", host, account.uid);
    Curl_headers_get headers { curl, token, url };

    if (!headers.perform())
        return;
}

Curl_headers_get Client::header(const std::string& url) const
{
    return { curl, token, std::format("{}/{}", host, url) };
}

Curl_headers_get Client::header_user(const std::string& url) const
{
    std::cout << "Header: " << std::format("{}/users/{}/{}", host, account.uid, url) << '\n';
    return { curl, token, std::format("{}/users/{}/{}", host, account.uid, url) };
}

} // namespace api
