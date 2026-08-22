# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_mower_hardware_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED mower_hardware_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(mower_hardware_FOUND FALSE)
  elseif(NOT mower_hardware_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(mower_hardware_FOUND FALSE)
  endif()
  return()
endif()
set(_mower_hardware_CONFIG_INCLUDED TRUE)

# output package information
if(NOT mower_hardware_FIND_QUIETLY)
  message(STATUS "Found mower_hardware: 0.0.0 (${mower_hardware_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'mower_hardware' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT ${mower_hardware_DEPRECATED_QUIET})
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(mower_hardware_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${mower_hardware_DIR}/${_extra}")
endforeach()
