#include "nlohmann/json.hpp"
#include <curl/curl.h>
#include <curl/easy.h>

using json = nlohmann::json;

namespace api {

struct Track;

struct Curl_headers_get {
    Curl_headers_get(CURL* curl, const std::string& token, const std::string& url);
    Curl_headers_get(const Curl_headers_get&) = delete;
    Curl_headers_get& operator=(const Curl_headers_get&) = delete;
    Curl_headers_get(Curl_headers_get&& other) noexcept;
    Curl_headers_get& operator=(Curl_headers_get&& other) noexcept;
    ~Curl_headers_get();

    bool perform() const;

    curl_slist* headers { nullptr };
    std::string responce;
    CURL* curl;
};

/// @brief Отличается от Curl_headers_get тем, что переходит по редиректам
struct Curl_headers_download {
    Curl_headers_download(CURL* curl, const std::string& token, const std::string& url);
    Curl_headers_download(const Curl_headers_download&) = delete;
    Curl_headers_download& operator=(const Curl_headers_download&) = delete;
    Curl_headers_download(Curl_headers_download&& other) = delete;
    Curl_headers_download& operator=(Curl_headers_download&& other) = delete;
    ~Curl_headers_download();

    bool perform() const;

    curl_slist* headers { nullptr };
    std::string responce;
    CURL* curl;
};


using id_t = unsigned long;

struct Account {
    Account() = default;
    explicit Account(const std::string& json_str);
    unsigned long uid { 0 };
    std::string first_name;
    std::string second_name;
    std::string display_name;
};

struct Client {
    explicit Client(std::string token);
    ~Client();

    Client(const Client&) = delete;
    Client(Client&&) = delete;
    Client& operator=(const Client&) = delete;
    Client& operator=(Client&&) = delete;

    CURL* curl = nullptr;
    std::string token;
    std::string_view host = "https://api.music.yandex.net";

    Account account;

    Curl_headers_get header_user(const std::string& url) const;
    Curl_headers_get header(const std::string& url) const;
    std::vector<Track> liked_tracks();
    void playlists();

private:
    void receive_account_info();
};

} // namespace api
