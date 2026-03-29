#include <curl/curl.h>
#include <curl/easy.h>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace api {

struct Client;

using id_t = unsigned long;

struct Cover {
    Cover() = default;
    explicit Cover(const nlohmann::basic_json<>&);
    std::string uri;
    std::string prefix;
};

struct Artist {
    explicit Artist(const nlohmann::basic_json<>&);
    id_t id;
    std::string name;
    Cover cover;
};

struct Album {
    explicit Album(const nlohmann::basic_json<>&);
    id_t id;
    unsigned int year;
    std::string title;
    std::string genre;
    std::vector<id_t> artists;
};

struct Download_info {
    Download_info() = default;
    explicit Download_info(const nlohmann::basic_json<>& json);
    std::string download_info_url;
    std::string codec;
    unsigned int bitrate { 0 };
};

struct Meta {
    Meta() = default;
    explicit Meta(const nlohmann::basic_json<>&);
    std::string title;
    unsigned long duration_ms { 0 };
    std::vector<Artist> artists;
    std::vector<Album> albums;
    std::vector<size_t> positions;
    std::string cover_uri;

    bool has_sync_lyrics { false };
    bool has_text_lyrics { false };
};

/// @todo Mulitple download info parse
struct Track {
    Track(Client* client, std::string id);
    ~Track();

    std::string id;
    Meta& meta();
    void download(const std::string&);
    void download_cover(const std::string&);

private:
    bool _fetched { false };
    Meta _meta;
    Client* _client;

    void fetch_download_info();
    Download_info _download;
};

} // namespace api
