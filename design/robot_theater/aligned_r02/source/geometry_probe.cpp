#include <iostream>
#include "config.h"

int main() {
    using namespace hexapod::config;
    std::cout << "{\"side_translation_mm\":" << kChassisSideTranslationMm
              << ",\"mount_side_x_mm\":" << kLegMountLeftRightX
              << ",\"mount_corner_x_mm\":" << kLegMountOtherX
              << ",\"mount_corner_y_mm\":" << kLegMountOtherY
              << ",\"link_lengths_mm\":[" << kLegRootToJoint1 << ','
              << kLegJoint1ToJoint2 << ',' << kLegJoint2ToJoint3 << ','
              << kLegJoint3ToTip << "]}" << std::endl;
}
