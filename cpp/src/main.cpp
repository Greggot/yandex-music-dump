
#include "api/api_client.h"
#include "api/api_track.h"
#include <curl/curl.h>
#include <format>
#include <fstream>
#include <iostream>
#include <taglib/attachedpictureframe.h>
#include <taglib/fileref.h>
#include <taglib/id3v2frame.h>
#include <taglib/id3v2tag.h>
#include <taglib/mpegfile.h>
#include <taglib/taglib.h>

namespace {

std::string compile_artists(const std::vector<api::Artist>& artists)
{
    std::string compilation {};
    for (const auto& artist : artists)
        compilation += artist.name + ", ";
    compilation.erase(compilation.size() - 2);
    return compilation;
}

void write_metadata(std::string title, const api::Meta& meta)
{
    std::ifstream image { std::format("{}.png", title), std::ios::binary | std::ios::ate };

    std::streamsize size = image.tellg();
    image.seekg(0, std::ios::beg);
    TagLib::ByteVector image_data((int)size, 0);
    image.read(image_data.data(), size);

    TagLib::MPEG::File f(std::format("{}.mp3", title).c_str());
    TagLib::ID3v2::Tag* tag = f.ID3v2Tag(true);

    if (tag) {
        auto* frame = new TagLib::ID3v2::AttachedPictureFrame; // NOLINT(cppcoreguidelines-owning-memory)
        frame->setMimeType("image/png");
        frame->setType(TagLib::ID3v2::AttachedPictureFrame::FrontCover);
        frame->setPicture(image_data);
        frame->setDescription("Front Cover");

        tag->removeFrames("APIC");
        tag->addFrame(frame);

        tag->setArtist(TagLib::String(compile_artists(meta.artists), TagLib::String::UTF8));
        tag->setAlbum(TagLib::String(meta.albums.front().title, TagLib::String::UTF8));
        tag->setTitle(TagLib::String(meta.title, TagLib::String::UTF8));
        tag->setGenre(TagLib::String(meta.albums.front().genre, TagLib::String::UTF8));
        tag->setYear(meta.albums.front().year);
        tag->setTrack(meta.positions.front());
        f.save();
    }
}

std::string file_name(api::Track& track)
{
    return std::format("{} - {}", compile_artists(track.meta().artists), track.meta().title);
}
} // namespace

int main(int argc, char* argv[])
{
    if (argc < 2) {
        std::cout << "Usage: play <token>\n";
        return 1;
    }

    api::Client client { argv[1] };
    auto likes = client.liked_tracks();
    std::cout << "Get " << likes.size() << " liked tracks\n";
    for (int i = 0; i < 5; ++i) {

        const auto filename = file_name(likes[i]);
        std::cout << std::format("  {} ({}, {})\n", filename, likes[i].meta().albums.front().title, likes[i].meta().albums.front().year);
        likes[i].download(std::format("{}.mp3", filename));
        likes[i].download_cover(std::format("{}.png", filename));
        write_metadata(filename, likes[i].meta());
    }
    return 0;
}