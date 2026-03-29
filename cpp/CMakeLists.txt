cmake_minimum_required(VERSION 3.5)
set(CMAKE_CXX_STANDARD 20)
project(ymapilib)

find_package(PNG REQUIRED)
find_package(CURL REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(PkgConfig REQUIRED)
find_package(nlohmann_json REQUIRED)
pkg_check_modules(TAGLIB REQUIRED IMPORTED_TARGET taglib)

set(SOURCES
    src/api/api_client.cpp
    src/api/api_track.cpp
)

add_executable(play src/main.cpp)
add_library(ymapi STATIC ${SOURCES})

target_include_directories(ymapi PUBLIC src)
target_link_libraries(ymapi PRIVATE ${CURL_LIBRARIES})
target_link_libraries(ymapi PRIVATE nlohmann_json::nlohmann_json)
target_link_libraries(ymapi PRIVATE ${OPENSSL_LIBRARIES})

target_include_directories(play PUBLIC src)
target_include_directories(play PRIVATE ${PNG_INCLUDE_DIR})
target_link_libraries(play PRIVATE ${PNG_LIBRARY})
target_link_libraries(play PRIVATE PkgConfig::TAGLIB)
target_link_libraries(play PRIVATE ymapi)

