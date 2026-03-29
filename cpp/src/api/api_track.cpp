#include "api/api_track.h"
#include "api/api_client.h"
#include <cstring>
#include <curl/curl.h>
#include <curl/easy.h>
#include <format>
#include <fstream>
#include <iostream>
#include <openssl/md5.h>

namespace api {

namespace {

const std::string_view sign_salt = "XGRlBW9FXlekgbPrRHuSiA";
std::string md5_hash(const std::vector<unsigned char>& input)
{
    std::array<unsigned char, MD5_DIGEST_LENGTH> digest {};
    MD5(input.data(), input.size(), digest.data());

    std::stringstream ss;
    for (unsigned char i : digest)
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)i;
    return ss.str();
}

std::string sign_download(const std::string_view& path, const std::string_view& s)
{
    std::string_view path_without_first { path.begin() + 1, path.end() };
    std::vector<unsigned char> data;
    data.resize(sign_salt.size() + path_without_first.size() + s.size());
    std::memcpy(data.data(), sign_salt.data(), sign_salt.size());
    std::memcpy(data.data() + sign_salt.size(), path.data() + 1, path.size() - 1);
    std::memcpy(data.data() + sign_salt.size() + path.size() - 1, s.data(), s.size());
    return md5_hash(data);
}

} // namespace

Track::Track(Client* client, std::string _id): id(std::move(_id)), _client(client)
{
}

Track::~Track() = default;

Meta& Track::meta()
{
    if (_fetched)
        return _meta;

    const auto url = std::format("tracks?track-ids={}&with-positions=false", id);
    auto header = _client->header(url);

    if (!header.perform())
        return _meta;

    auto json = json::parse(header.responce)["result"][0];
    _meta = Meta(json);
    _fetched = true;

    return _meta;
}

Cover::Cover(const nlohmann::basic_json<>& json):
    uri(json["uri"])
{
}

Artist::Artist(const nlohmann::basic_json<>& json):
    id(json["id"]),
    name(json["name"])
{
    if (json.contains("cover"))
        cover = Cover(json["cover"]);
}

Album::Album(const nlohmann::basic_json<>& json):
    id(json["id"]),
    year(json["year"]),
    title(json["title"]),
    genre(json["genre"])
{
    for (const auto& artist : json["artists"])
        artists.push_back(artist["id"]);
}

Meta::Meta(const nlohmann::basic_json<>& json):
    title(json["title"]),
    duration_ms(json["durationMs"]),
    cover_uri(json["coverUri"])
{
    for (const auto& album : json["albums"]) {
        albums.emplace_back(album);
        positions.emplace_back(album["trackPosition"]["index"]);
    }
    for (const auto& artist : json["artists"])
        artists.emplace_back(artist);
}

void Track::download(const std::string& download_path)
{
    fetch_download_info();

    Curl_headers_download header_download { _client->curl, _client->token, _download.download_info_url };
    if (!header_download.perform())
        return;

    const auto& str = header_download.responce;
    size_t i = str.find("<host>");
    size_t j = str.find("</host>", i);
    std::string_view host { str.begin() + i + 6, str.begin() + j };

    i = str.find("<path>", j);
    j = str.find("</path>", i);
    std::string_view path { str.begin() + i + 6, str.begin() + j };

    i = str.find("<ts>", j);
    j = str.find("</ts>", i);
    std::string_view ts { str.begin() + i + 4, str.begin() + j };

    i = str.find("<s>", j);
    j = str.find("</s>", i);
    std::string_view s { str.begin() + i + 3, str.begin() + j };

    std::string download_url = std::format("https://{}/get-mp3/{}/{}{}",
        host, sign_download(path, s), ts, path);

    Curl_headers_download header_real_download { _client->curl, _client->token, download_url };
    if (header_real_download.perform()) {
        std::ofstream file(download_path);
        file << header_real_download.responce;
    }
}

void Track::fetch_download_info()
{
    const auto url = std::format("tracks/{}/download-info", id);
    auto header = _client->header(url);

    if (header.perform()) {
        const auto json = json::parse(header.responce)["result"][0];

        std::ofstream file("download_info.json");
        file << json;
        _download = Download_info(json);
    }
}

Download_info::Download_info(const nlohmann::basic_json<>& json):
    download_info_url(json["downloadInfoUrl"]),
    codec(json["codec"]),
    bitrate(json["bitrateInKbps"])
{
}

void Track::download_cover(const std::string& path)
{
    std::string url = meta().cover_uri;
    url.pop_back();
    url.pop_back();
    url += "200x200";

    Curl_headers_download header_real_download { _client->curl, _client->token, url };
    if (header_real_download.perform()) {
        std::ofstream file(path);
        file << header_real_download.responce;
    }
}

} // namespace api
