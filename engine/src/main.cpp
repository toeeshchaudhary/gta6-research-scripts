// GTA6 engine v0: Win32 + Vulkan viewer for real GTA VI drawable geometry and textures.
//
// Renders an extracted .OBJ (real game model) with a real extracted .DDS (real game
// texture) through a Vulkan pipeline at 1280x720, measures frame time, and can dump a
// frame to PNG. See ../ENGINE.md.

#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <psapi.h>
#include <vulkan/vulkan.h>
#include <vulkan/vulkan_win32.h>

#include <algorithm>
#include <cstdarg>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "dds_loader.h"
#include "math3d.h"
#include "obj_loader.h"
#include "png_writer.h"
#include "scene.h"

static void logf_(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    vprintf("\n", nullptr);
    fflush(stdout);
}

#define LOG(...) logf_(__VA_ARGS__)
#define VK_CHECK(x, what)                                                    \
    do {                                                                     \
        VkResult r_ = (x);                                                    \
        if (r_ != VK_SUCCESS) {                                               \
            LOG("[fatal] %s -> VkResult %d", what, (int)r_);                  \
            return false;                                                     \
        }                                                                     \
    } while (0)

static void LOG_RESULT(VkResult r) { (void)r; }

// M3 display scale: multiplies every instance's own scale. True transforms stay
// true in position and orientation; this only makes 2-unit props legible from
// the overview altitude. 1.0 = exactly the data.
struct Args {
    int width = 1280;
    int height = 720;
    int reps = 1;
    int frames = 300;
    int warmup = 30;
    int captureFrame = 0; // 0 = derive from frames+warmup
    bool validate = false;
    bool fsDbg = false;
    bool hashEmpty = false;
    bool texSynth = false;
    bool meshMode = false;
    std::string vsName;
    std::string psName;
    bool vsync = false;
    std::string model;
    std::string texture;
    std::string shot = "shot.png";
    // ---- M3 scene ----
    std::string scene;              // --scene <json>: data, not hard-coded
    int limit = 0;                  // --limit N: evenly spaced subset
    std::string view = "overview";  // --view overview|street|block
    float displayScale = 1.0f;      // --scale K: legibility multiplier
    bool cull = true;               // --no-cull disables backface culling
    bool noFrustum = false;         // --no-frustum disables instance culling
    float spinDeg = 0.0f;           // --spin D: synthetic yaw on top of the quaternion
    std::string pool;               // --pool a.obj,b.obj
    std::string camPos, camLook;    // --cam x,y,z --look x,y,z
    bool noise = false;             // --noise N: reported as noise, not instances
    bool blitTest = false;          // --blit-test: one giant clip-space triangle
    // ---- M4: true scale, ground, sky, statistics ----
    bool normalize = false;         // --norm restores the old unit-sphere rescale
    bool ground = true;             // --no-ground: keep the export's own vertical origin
    bool sky = false;               // --sky: sky-blue clear colour instead of near-black
    bool groundPlane = false;       // --ground-plane: synthetic road/sidewalk
    bool stats = false;             // --stats: report peak working set
};

struct App {
    HINSTANCE hinst = nullptr;
    HWND hwnd = nullptr;
    bool running = true;
    bool resizePending = false;

    VkInstance instance = VK_NULL_HANDLE;
    VkSurfaceKHR surface = VK_NULL_HANDLE;
    VkPhysicalDevice phys = VK_NULL_HANDLE;
    VkDevice dev = VK_NULL_HANDLE;
    uint32_t queueFamily = 0;
    VkQueue queue = VK_NULL_HANDLE;

    VkSwapchainKHR swapchain = VK_NULL_HANDLE;
    VkFormat swFormat = VK_FORMAT_B8G8R8A8_UNORM;
    VkExtent2D extent{};
    std::vector<VkImage> swImages;
    std::vector<VkImageView> swViews;

    VkImage color = VK_NULL_HANDLE;
    VkDeviceMemory colorMem = VK_NULL_HANDLE;
    VkImageView colorView = VK_NULL_HANDLE;
    VkImage depth = VK_NULL_HANDLE;
    VkDeviceMemory depthMem = VK_NULL_HANDLE;
    VkImageView depthView = VK_NULL_HANDLE;

    VkRenderPass renderPass = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkPipelineLayout pipeLayout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkDescriptorSetLayout setLayout = VK_NULL_HANDLE;
    VkDescriptorPool descPool = VK_NULL_HANDLE;
    VkDescriptorSet descSet = VK_NULL_HANDLE;

    VkCommandPool cmdPool = VK_NULL_HANDLE;
    VkCommandBuffer cmd = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    VkSemaphore semAcquire = VK_NULL_HANDLE;
    VkSemaphore semRender = VK_NULL_HANDLE;

    VkBuffer vbuf = VK_NULL_HANDLE;
    VkDeviceMemory vbMem = VK_NULL_HANDLE;
    VkBuffer ibuf = VK_NULL_HANDLE;
    VkDeviceMemory ibMem = VK_NULL_HANDLE;
    uint32_t indexCount = 0;

    VkImage tex = VK_NULL_HANDLE;
    VkDeviceMemory texMem = VK_NULL_HANDLE;
    VkImageView texView = VK_NULL_HANDLE;
    VkSampler sampler = VK_NULL_HANDLE;
    uint32_t texLevels = 0;

    VkBuffer ubo = VK_NULL_HANDLE;
    VkDeviceMemory uboMem = VK_NULL_HANDLE;
    void* uboMap = nullptr;

    // ---- M2: game-shader runtime state (see ENGINE_M2.md) ------------------
    // One buffer-device-address heap; every shader access is heap_base + Xbox VA.
    VkBuffer heap = VK_NULL_HANDLE;
    VkDeviceMemory heapMem = VK_NULL_HANDLE;
    uint8_t* heapMap = nullptr;
    VkDeviceAddress heapBda = 0;
    VkBuffer hashBuf = VK_NULL_HANDLE;
    VkDeviceMemory hashMem = VK_NULL_HANDLE;
    uint32_t* hashMap = nullptr;
    uint32_t hashMask = 2047; // 2048 slots for up to ~950 models + the S# key
    VkImage fbTex = VK_NULL_HANDLE;
    VkDeviceMemory fbTexMem = VK_NULL_HANDLE;
    VkImageView fbTexView = VK_NULL_HANDLE;
    VkSampler fbSampler = VK_NULL_HANDLE;
    // 144-byte push block: dwords 0-31 = user SGPRs, 32-33 = heap base,
    // 34-35 = code base.
    uint8_t push[144] = {0};
    // Descriptors at index 0 are fallbacks (blatant magenta) so a hash miss shows.
    uint32_t fallbackHits = 0;
    uint32_t fallbackImage = 0;
    uint32_t shaderImage = 1;
    bool gsMode = false;
    bool hashEmpty = false;
    bool texSynth = false;
    bool meshMode = false;

    VkBuffer readback = VK_NULL_HANDLE;
    VkDeviceMemory readbackMem = VK_NULL_HANDLE;
    void* readbackMap = nullptr;
    VkDeviceSize readbackSize = 0;

    Mesh mesh;
    DdsImage texData;
    float time = 0.0f;
    int reps = 1;
    int frameIdx = 0;
    int captureFrame = 0;
    char gpuName[256] = {0};

    // ---- M3: scene instancing -------------------------------------------
    bool sceneMode = false;
    bool blitTest = false;
    Scene scene;
    std::vector<Mesh> pool;             // representative models, one per pool slot
    std::vector<std::string> poolNames;
    std::vector<VkImage> modelTex;
    std::vector<VkDeviceMemory> modelTexMem;
    std::vector<VkImageView> modelTexView;
    std::vector<VkSampler> modelSamp;
    std::vector<uint32_t> modelVa;      // heap VA of each model's T#
    std::vector<uint32_t> modelImg;     // descriptor image index used by each model's T#
    std::vector<std::vector<uint32_t>> modelIndices; // per-model index list (local)
    // Rebuilt every frame: one contiguous slab per model in world/clip space.
    VkBuffer dynVbo = VK_NULL_HANDLE;
    VkDeviceMemory dynVboMem = VK_NULL_HANDLE;
    MeshVertex* dynVboMap = nullptr;
    VkBuffer dynIbo = VK_NULL_HANDLE;
    VkDeviceMemory dynIboMem = VK_NULL_HANDLE;
    uint32_t* dynIboMap = nullptr;
    VkDeviceSize dynVboBytes = 0, dynIboBytes = 0;
    std::vector<uint32_t> modelDrawOffset; // sub-range per model, rebuilt per frame
    std::vector<uint32_t> modelDrawCount;
    uint32_t drawnInstances = 0, culledInstances = 0, drawnTris = 0, drawnVerts = 0, drawnDraws = 0;
    Vec3 camEye, camTarget;
    float camNear = 0.1f, camFar = 1000.0f;
    bool userCam = false;
};

struct PushConst {
    Mat4 mvp;
    Mat4 model;
};
static_assert(sizeof(PushConst) == 128, "push constant size");

struct UboData {
    float lightDir[4];
    float camPos[4];
    float params[4];
};

static VkFormat g_depthFormat = VK_FORMAT_D32_SFLOAT;
static std::string g_psName = "ps_passthrough_copy";
static std::string g_vsName = "vs_passthrough";
// M3: back-face culling on for scene draws (the OBJ faces are CCW-outward);
// the mesh modes keep it off by default.
static VkCullModeFlags g_cull = VK_CULL_MODE_NONE;

static uint32_t findMemoryType(VkPhysicalDevice pd, uint32_t bits, VkMemoryPropertyFlags props) {
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(pd, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; ++i) {
        if ((bits & (1u << i)) && (mp.memoryTypes[i].propertyFlags & props) == props) return i;
    }
    return UINT32_MAX;
}

static bool createBuffer(App& a, VkDeviceSize size, VkBufferUsageFlags usage, VkMemoryPropertyFlags props,
                         VkBuffer& buf, VkDeviceMemory& mem) {
    VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    bi.size = size;
    bi.usage = usage;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VK_CHECK(vkCreateBuffer(a.dev, &bi, nullptr, &buf), "vkCreateBuffer");
    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(a.dev, buf, &req);
    VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = findMemoryType(a.phys, req.memoryTypeBits, props);
    if (ai.memoryTypeIndex == UINT32_MAX) {
        LOG("[fatal] no memory type for buffer");
        return false;
    }
    VK_CHECK(vkAllocateMemory(a.dev, &ai, nullptr, &mem), "vkAllocateMemory(buffer)");
    VK_CHECK(vkBindBufferMemory(a.dev, buf, mem, 0), "vkBindBufferMemory");
    return true;
}

// ---------------------------------------------------------------- shaders

static bool readFile(const std::string& path, std::vector<uint8_t>& out) {
    FILE* f = nullptr;
    if (fopen_s(&f, path.c_str(), "rb") != 0 || !f) return false;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n <= 0) {
        fclose(f);
        return false;
    }
    out.resize((size_t)n);
    size_t got = fread(out.data(), 1, (size_t)n, f);
    fclose(f);
    return got == (size_t)n;
}

static std::string exeDir() {
    char buf[MAX_PATH];
    GetModuleFileNameA(nullptr, buf, MAX_PATH);
    std::string s(buf);
    size_t pos = s.find_last_of("\\/");
    return pos == std::string::npos ? std::string(".") : s.substr(0, pos);
}

static bool makeShader(App& a, const std::string& path, VkShaderModule& out) {
    std::vector<uint8_t> code;
    if (!readFile(path, code)) {
        LOG("[fatal] cannot read shader %s", path.c_str());
        return false;
    }
    VkShaderModuleCreateInfo ci{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
    ci.codeSize = code.size();
    ci.pCode = (const uint32_t*)code.data();
    VK_CHECK(vkCreateShaderModule(a.dev, &ci, nullptr, &out), "vkCreateShaderModule");
    return true;
}

// ---------------------------------------------------------------- window

static LRESULT CALLBACK wndProc(HWND h, UINT msg, WPARAM wp, LPARAM lp) {
    App* a = (App*)GetWindowLongPtrA(h, GWLP_USERDATA);
    switch (msg) {
        case WM_CLOSE:
            PostQuitMessage(0);
            return 0;
        case WM_SIZE:
            if (a && wp != SIZE_MINIMIZED) a->resizePending = true;
            return 0;
        case WM_KEYDOWN:
            if (wp == VK_ESCAPE) PostQuitMessage(0);
            return 0;
        default:
            break;
    }
    return DefWindowProcA(h, msg, wp, lp);
}

static bool createWindow(App& a, const Args& args) {
    WNDCLASSEXA wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = wndProc;
    wc.hInstance = a.hinst;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = "GTA6EngineWindow";
    if (!RegisterClassExA(&wc)) {
        LOG("[fatal] RegisterClassEx failed");
        return false;
    }
    RECT r{0, 0, args.width, args.height};
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    a.hwnd = CreateWindowExA(0, wc.lpszClassName, "GTA6 engine M3 - scene instances at true world transforms",
                             WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, r.right - r.left,
                             r.bottom - r.top, nullptr, nullptr, a.hinst, nullptr);
    if (!a.hwnd) {
        LOG("[fatal] CreateWindowEx failed");
        return false;
    }
    SetWindowLongPtrA(a.hwnd, GWLP_USERDATA, (LONG_PTR)&a);
    ShowWindow(a.hwnd, SW_SHOW);
    UpdateWindow(a.hwnd);
    LOG("[stage] window created %dx%d", args.width, args.height);
    return true;
}

// ---------------------------------------------------------------- vulkan init

static bool createInstance(App& a, const Args& args) {
    VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
    app.pApplicationName = "GTA6 engine v0";
    app.apiVersion = VK_API_VERSION_1_2;

    uint32_t extCount = 0;
    vkEnumerateInstanceExtensionProperties(nullptr, &extCount, nullptr);
    std::vector<VkExtensionProperties> exts(extCount);
    vkEnumerateInstanceExtensionProperties(nullptr, &extCount, exts.data());
    const char* wanted[] = {"VK_KHR_surface", "VK_KHR_win32_surface"};
    std::vector<const char*> enabled;
    for (const char* w : wanted) {
        bool found = false;
        for (auto& e : exts)
            if (strcmp(e.extensionName, w) == 0) found = true;
        if (!found) {
            LOG("[fatal] missing instance extension %s", w);
            return false;
        }
        enabled.push_back(w);
    }

    std::vector<const char*> layers;
    const char* wantLayer = "VK_LAYER_KHRONOS_validation";
    if (args.validate) {
        uint32_t lc = 0;
        vkEnumerateInstanceLayerProperties(&lc, nullptr);
        std::vector<VkLayerProperties> ls(lc);
        vkEnumerateInstanceLayerProperties(&lc, ls.data());
        for (auto& l : ls)
            if (strcmp(l.layerName, wantLayer) == 0) layers.push_back(wantLayer);
        if (layers.empty()) LOG("[warn] validation layer not found");
    }

    VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    ci.pApplicationInfo = &app;
    ci.enabledExtensionCount = (uint32_t)enabled.size();
    ci.ppEnabledExtensionNames = enabled.data();
    ci.enabledLayerCount = (uint32_t)layers.size();
    ci.ppEnabledLayerNames = layers.data();
    VK_CHECK(vkCreateInstance(&ci, nullptr, &a.instance), "vkCreateInstance");
    LOG("[stage] instance created (%s)", layers.empty() ? "no validation" : "validation enabled");
    return true;
}

static bool createSurface(App& a) {
    VkWin32SurfaceCreateInfoKHR ci{VK_STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR};
    ci.hinstance = a.hinst;
    ci.hwnd = a.hwnd;
    VK_CHECK(vkCreateWin32SurfaceKHR(a.instance, &ci, nullptr, &a.surface), "vkCreateWin32SurfaceKHR");
    return true;
}

static bool pickDevice(App& a) {
    uint32_t count = 0;
    VK_CHECK(vkEnumeratePhysicalDevices(a.instance, &count, nullptr), "vkEnumeratePhysicalDevices");
    if (count == 0) {
        LOG("[fatal] no Vulkan physical devices");
        return false;
    }
    std::vector<VkPhysicalDevice> devs(count);
    vkEnumeratePhysicalDevices(a.instance, &count, devs.data());

    VkPhysicalDevice chosen = VK_NULL_HANDLE;
    uint32_t chosenFamily = 0;
    for (auto d : devs) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(d, &p);
        uint32_t qc = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(d, &qc, nullptr);
        std::vector<VkQueueFamilyProperties> qs(qc);
        vkGetPhysicalDeviceQueueFamilyProperties(d, &qc, qs.data());
        for (uint32_t i = 0; i < qc; ++i) {
            VkBool32 present = VK_FALSE;
            vkGetPhysicalDeviceSurfaceSupportKHR(d, i, a.surface, &present);
            if ((qs[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) && present) {
                chosen = d;
                chosenFamily = i;
                break;
            }
        }
        if (chosen) {
            snprintf(a.gpuName, sizeof(a.gpuName), "%s", p.deviceName);
            LOG("[stage] device: %s (api %u.%u.%u)", p.deviceName, VK_VERSION_MAJOR(p.apiVersion),
                VK_VERSION_MINOR(p.apiVersion), VK_VERSION_PATCH(p.apiVersion));
            break;
        }
    }
    if (!chosen) {
        LOG("[fatal] no graphics+present queue family");
        return false;
    }

    VkPhysicalDeviceFeatures feats{};
    std::vector<const char*> exts = {VK_KHR_SWAPCHAIN_EXTENSION_NAME};
    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
    qci.queueFamilyIndex = chosenFamily;
    qci.queueCount = 1;
    qci.pQueuePriorities = &prio;

    // Vulkan 1.2 core features the translated shaders need: buffer device
    // address (PhysicalStorageBuffer64) and runtime/bindless descriptor arrays.
    VkPhysicalDeviceVulkan12Features v12{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES};
    v12.bufferDeviceAddress = VK_TRUE;
    v12.runtimeDescriptorArray = VK_TRUE;
    v12.descriptorBindingPartiallyBound = VK_TRUE;
    v12.shaderSampledImageArrayNonUniformIndexing = VK_TRUE;
    v12.descriptorBindingSampledImageUpdateAfterBind = VK_TRUE;
    v12.shaderStorageBufferArrayNonUniformIndexing = VK_TRUE;
    VkPhysicalDeviceFeatures2 feats2{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2};
    feats2.pNext = &v12;
    feats2.features.shaderInt64 = VK_TRUE;

    VkDeviceCreateInfo dci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos = &qci;
    dci.pNext = &feats2;
    dci.pEnabledFeatures = nullptr;
    dci.enabledExtensionCount = (uint32_t)exts.size();
    dci.ppEnabledExtensionNames = exts.data();
    VK_CHECK(vkCreateDevice(chosen, &dci, nullptr, &a.dev), "vkCreateDevice");
    a.phys = chosen;
    a.queueFamily = chosenFamily;
    vkGetDeviceQueue(a.dev, chosenFamily, 0, &a.queue);
    LOG("[stage] device created (graphics+present queue family %u)", chosenFamily);
    return true;
}

static bool createSwapchain(App& a, const Args& args) {
    VkSurfaceCapabilitiesKHR caps;
    VK_CHECK(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(a.phys, a.surface, &caps), "surface caps");

    uint32_t fc = 0;
    vkGetPhysicalDeviceSurfaceFormatsKHR(a.phys, a.surface, &fc, nullptr);
    std::vector<VkSurfaceFormatKHR> formats(fc);
    vkGetPhysicalDeviceSurfaceFormatsKHR(a.phys, a.surface, &fc, formats.data());
    VkSurfaceFormatKHR chosen = formats.empty() ? VkSurfaceFormatKHR{VK_FORMAT_B8G8R8A8_UNORM, VK_COLOR_SPACE_SRGB_NONLINEAR_KHR}
                                                : formats[0];
    for (auto& f : formats) {
        if (f.format == VK_FORMAT_B8G8R8A8_UNORM) chosen = f;
    }

    uint32_t pc = 0;
    vkGetPhysicalDeviceSurfacePresentModesKHR(a.phys, a.surface, &pc, nullptr);
    std::vector<VkPresentModeKHR> modes(pc);
    vkGetPhysicalDeviceSurfacePresentModesKHR(a.phys, a.surface, &pc, modes.data());
    VkPresentModeKHR mode = VK_PRESENT_MODE_FIFO_KHR;
    for (auto m : modes)
        if (m == VK_PRESENT_MODE_IMMEDIATE_KHR && !args.vsync) mode = m;

    VkExtent2D ext;
    if (caps.currentExtent.width != UINT32_MAX) {
        ext = caps.currentExtent;
    } else {
        ext.width = std::clamp((uint32_t)args.width, caps.minImageExtent.width, caps.maxImageExtent.width);
        ext.height = std::clamp((uint32_t)args.height, caps.minImageExtent.height, caps.maxImageExtent.height);
    }

    uint32_t images = caps.minImageCount + 1;
    if (caps.maxImageCount && images > caps.maxImageCount) images = caps.maxImageCount;

    VkSwapchainCreateInfoKHR ci{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};
    ci.surface = a.surface;
    ci.minImageCount = images;
    ci.imageFormat = chosen.format;
    ci.imageColorSpace = chosen.colorSpace;
    ci.imageExtent = ext;
    ci.imageArrayLayers = 1;
    ci.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    ci.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.preTransform = caps.currentTransform;
    ci.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    ci.presentMode = mode;
    ci.clipped = VK_TRUE;
    VK_CHECK(vkCreateSwapchainKHR(a.dev, &ci, nullptr, &a.swapchain), "vkCreateSwapchainKHR");

    uint32_t n = 0;
    vkGetSwapchainImagesKHR(a.dev, a.swapchain, &n, nullptr);
    a.swImages.resize(n);
    vkGetSwapchainImagesKHR(a.dev, a.swapchain, &n, a.swImages.data());
    a.swViews.resize(n);
    for (uint32_t i = 0; i < n; ++i) {
        VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        vi.image = a.swImages[i];
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = chosen.format;
        vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        VK_CHECK(vkCreateImageView(a.dev, &vi, nullptr, &a.swViews[i]), "vkCreateImageView(swap)");
    }
    a.swFormat = chosen.format;
    a.extent = ext;
    LOG("[stage] swapchain %ux%u, %u images, format %d, present mode %d", ext.width, ext.height, n,
        (int)chosen.format, (int)mode);
    return true;
}

static bool createImage2D(App& a, uint32_t w, uint32_t h, VkFormat fmt, VkImageUsageFlags usage,
                          VkImageAspectFlags aspect, VkImage& img, VkDeviceMemory& mem, VkImageView& view) {
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.imageType = VK_IMAGE_TYPE_2D;
    ci.format = fmt;
    ci.extent = {w, h, 1};
    ci.mipLevels = 1;
    ci.arrayLayers = 1;
    ci.samples = VK_SAMPLE_COUNT_1_BIT;
    ci.tiling = VK_IMAGE_TILING_OPTIMAL;
    ci.usage = usage;
    ci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VK_CHECK(vkCreateImage(a.dev, &ci, nullptr, &img), "vkCreateImage");
    VkMemoryRequirements req;
    vkGetImageMemoryRequirements(a.dev, img, &req);
    VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = findMemoryType(a.phys, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (ai.memoryTypeIndex == UINT32_MAX) {
        LOG("[fatal] no device-local memory for image");
        return false;
    }
    VK_CHECK(vkAllocateMemory(a.dev, &ai, nullptr, &mem), "vkAllocateMemory(image)");
    VK_CHECK(vkBindImageMemory(a.dev, img, mem, 0), "vkBindImageMemory");
    VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
    vi.image = img;
    vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
    vi.format = fmt;
    vi.subresourceRange = {aspect, 0, 1, 0, 1};
    VK_CHECK(vkCreateImageView(a.dev, &vi, nullptr, &view), "vkCreateImageView");
    return true;
}

static bool createRenderPass(App& a) {
    VkAttachmentDescription att[2]{};
    att[0].format = a.swFormat;
    att[0].samples = VK_SAMPLE_COUNT_1_BIT;
    att[0].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    att[0].storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    att[0].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    att[0].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    att[0].initialLayout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    att[0].finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
    att[1].format = g_depthFormat;
    att[1].samples = VK_SAMPLE_COUNT_1_BIT;
    att[1].loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    att[1].storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    att[1].stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    att[1].stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    att[1].initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    att[1].finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    VkAttachmentReference colorRef{0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkAttachmentReference depthRef{1, VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL};
    VkSubpassDescription sp{};
    sp.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    sp.colorAttachmentCount = 1;
    sp.pColorAttachments = &colorRef;
    sp.pDepthStencilAttachment = &depthRef;

    VkSubpassDependency dep{};
    dep.srcSubpass = VK_SUBPASS_EXTERNAL;
    dep.dstSubpass = 0;
    dep.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_TRANSFER_BIT;
    dep.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT | VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dep.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
    dep.dstAccessMask =
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT | VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo ci{VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO};
    ci.attachmentCount = 2;
    ci.pAttachments = att;
    ci.subpassCount = 1;
    ci.pSubpasses = &sp;
    ci.dependencyCount = 1;
    ci.pDependencies = &dep;
    VK_CHECK(vkCreateRenderPass(a.dev, &ci, nullptr, &a.renderPass), "vkCreateRenderPass");
    return true;
}

static bool createPipeline(App& a) {
    VkShaderModule vs = VK_NULL_HANDLE, fs = VK_NULL_HANDLE;
    std::string dir = exeDir();
    if (!makeShader(a, dir + "\\shaders\\gs\\" + g_vsName + ".spv", vs)) return false;
    if (a.gsMode)
        if (!makeShader(a, dir + "\\shaders\\gs\\dbg_const.frag.spv", fs)) return false;
    if (!fs)
        if (!makeShader(a, dir + "\\shaders\\gs\\" + g_psName + ".spv", fs)) return false;

    VkPipelineShaderStageCreateInfo stages[2]{};
    stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = vs;
    stages[0].pName = "main";
    stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = fs;
    stages[1].pName = "main";

    // The game's VS reads SV_VertexID only (the vertex-fetch program is gone),
    // so there is no vertex input state at all: the shader synthesizes its
    // fullscreen triangle from gl_VertexIndex.
    // Mesh VS path: input locations are the game's D3D input registers
    // (0 = POSITION vec3, 1 = TEXCOORD vec2) per the contract, read out of the
    // engine's own interleaved vertex buffer.
    VkVertexInputBindingDescription vbind{0, sizeof(MeshVertex), VK_VERTEX_INPUT_RATE_VERTEX};
    VkVertexInputAttributeDescription vattr[2]{};
    vattr[0] = {0, 0, VK_FORMAT_R32G32B32_SFLOAT, (uint32_t)offsetof(MeshVertex, pos)};
    vattr[1] = {1, 0, VK_FORMAT_R32G32_SFLOAT, (uint32_t)offsetof(MeshVertex, u)};
    VkPipelineVertexInputStateCreateInfo vi{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    if (a.meshMode) {
        vi.vertexBindingDescriptionCount = 1;
        vi.pVertexBindingDescriptions = &vbind;
        vi.vertexAttributeDescriptionCount = 2;
        vi.pVertexAttributeDescriptions = vattr;
    }

    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
    ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    VkPipelineViewportStateCreateInfo vp{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
    vp.viewportCount = 1;
    vp.scissorCount = 1;

    VkPipelineRasterizationStateCreateInfo rs{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
    rs.polygonMode = VK_POLYGON_MODE_FILL;
    rs.cullMode = g_cull;
    // perspective() flips Y, which reverses screen-space winding: the OBJ faces
    // are CCW-outward in model space, so from the camera they are CW.
    rs.frontFace = g_cull != VK_CULL_MODE_NONE ? VK_FRONT_FACE_CLOCKWISE
                                               : VK_FRONT_FACE_COUNTER_CLOCKWISE;
    rs.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
    ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    VkPipelineDepthStencilStateCreateInfo ds{VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO};
    ds.depthTestEnable = a.meshMode ? VK_TRUE : VK_FALSE;
    ds.depthWriteEnable = a.meshMode ? VK_TRUE : VK_FALSE;
    ds.depthCompareOp = VK_COMPARE_OP_LESS_OR_EQUAL;

    VkPipelineColorBlendAttachmentState cba{};
    cba.colorWriteMask = 0xF;
    VkPipelineColorBlendStateCreateInfo cb{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
    cb.attachmentCount = 1;
    cb.pAttachments = &cba;

    VkDynamicState dyn[2] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
    VkPipelineDynamicStateCreateInfo dyns{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
    dyns.dynamicStateCount = 2;
    dyns.pDynamicStates = dyn;

    // 144-byte push block, both stages: dwords 0-31 user SGPRs, 32-33 heap base,
    // 34-35 code base.
    VkPushConstantRange pcr{VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0, 144};
    VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
    pl.setLayoutCount = 1;
    pl.pSetLayouts = &a.setLayout;
    pl.pushConstantRangeCount = 1;
    pl.pPushConstantRanges = &pcr;
    VK_CHECK(vkCreatePipelineLayout(a.dev, &pl, nullptr, &a.pipeLayout), "vkCreatePipelineLayout");

    VkGraphicsPipelineCreateInfo pci{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};
    pci.stageCount = 2;
    pci.pStages = stages;
    pci.pVertexInputState = &vi;
    pci.pInputAssemblyState = &ia;
    pci.pViewportState = &vp;
    pci.pRasterizationState = &rs;
    pci.pMultisampleState = &ms;
    pci.pDepthStencilState = &ds;
    pci.pColorBlendState = &cb;
    pci.pDynamicState = &dyns;
    pci.layout = a.pipeLayout;
    pci.renderPass = a.renderPass;
    pci.subpass = 0;
    LARGE_INTEGER pf, p0, p1;
    QueryPerformanceFrequency(&pf);
    QueryPerformanceCounter(&p0);
    VK_CHECK(vkCreateGraphicsPipelines(a.dev, VK_NULL_HANDLE, 1, &pci, nullptr, &a.pipeline),
             "vkCreateGraphicsPipelines");
    QueryPerformanceCounter(&p1);
    LOG("[perf] vkCreateGraphicsPipelines cpu %.1f ms",
        (double)(p1.QuadPart - p0.QuadPart) * 1000.0 / (double)pf.QuadPart);
    vkDestroyShaderModule(a.dev, vs, nullptr);
    vkDestroyShaderModule(a.dev, fs, nullptr);
    LOG("[stage] pipeline created from game SPIR-V (%s + %s, mesh=%d)", g_vsName.c_str(),
        g_psName.c_str(), (int)a.meshMode);
    return true;
}

// Bindless set 0 exactly as the translator's contract documents it: 0 = 2D
// sampled images, 1 = samplers, 2 = descriptor hash table. Every array is
// partially bound so only the used indices have to be written.
static const uint32_t kBindSlotCount = 64;

static bool createDescriptorLayout(App& a) {
    VkDescriptorSetLayoutBinding binds[3]{};
    VkDescriptorBindingFlags flags[3] = {VK_DESCRIPTOR_BINDING_PARTIALLY_BOUND_BIT,
                                         VK_DESCRIPTOR_BINDING_PARTIALLY_BOUND_BIT, 0};
    binds[0].binding = 0;
    binds[0].descriptorType = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
    binds[0].descriptorCount = kBindSlotCount;
    binds[0].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    binds[1].binding = 1;
    binds[1].descriptorType = VK_DESCRIPTOR_TYPE_SAMPLER;
    binds[1].descriptorCount = kBindSlotCount;
    binds[1].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    binds[2].binding = 2;
    binds[2].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    binds[2].descriptorCount = 1;
    binds[2].stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;

    VkDescriptorSetLayoutBindingFlagsCreateInfo fci{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_BINDING_FLAGS_CREATE_INFO};
    fci.bindingCount = 3;
    fci.pBindingFlags = flags;
    VkDescriptorSetLayoutCreateInfo ci{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
    ci.pNext = &fci;
    ci.bindingCount = 3;
    ci.pBindings = binds;
    VK_CHECK(vkCreateDescriptorSetLayout(a.dev, &ci, nullptr, &a.setLayout), "vkCreateDescriptorSetLayout");

    VkDescriptorPoolSize sizes[3] = {{VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE, kBindSlotCount},
                                     {VK_DESCRIPTOR_TYPE_SAMPLER, kBindSlotCount},
                                     {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1}};
    VkDescriptorPoolCreateInfo pci{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
    pci.maxSets = 1;
    pci.poolSizeCount = 3;
    pci.pPoolSizes = sizes;
    VK_CHECK(vkCreateDescriptorPool(a.dev, &pci, nullptr, &a.descPool), "vkCreateDescriptorPool");
    VkDescriptorSetAllocateInfo ai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
    ai.descriptorPool = a.descPool;
    ai.descriptorSetCount = 1;
    ai.pSetLayouts = &a.setLayout;
    VK_CHECK(vkAllocateDescriptorSets(a.dev, &ai, &a.descSet), "vkAllocateDescriptorSets");
    LOG("[stage] descriptor set 0: bindless image[%u] sampler[%u] hash-table", kBindSlotCount,
        kBindSlotCount);
    return true;
}

// ---------------------------------------------------------------- payload

static bool uploadMesh(App& a) {
    VkDeviceSize vsize = a.mesh.vertices.size() * sizeof(MeshVertex);
    VkDeviceSize isize = a.mesh.indices.size() * sizeof(uint32_t);
    if (!createBuffer(a, vsize, VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, a.vbuf,
                      a.vbMem))
        return false;
    if (!createBuffer(a, isize, VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, a.ibuf,
                      a.ibMem))
        return false;
    void* p = nullptr;
    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(a.dev, a.vbuf, &req);
    VkMemoryRequirements req2;
    vkGetBufferMemoryRequirements(a.dev, a.ibuf, &req2);
    (void)req;
    (void)req2;
    VK_CHECK(vkMapMemory(a.dev, a.vbMem, 0, vsize, 0, &p), "map vertex buffer");
    memcpy(p, a.mesh.vertices.data(), (size_t)vsize);
    vkUnmapMemory(a.dev, a.vbMem);
    VK_CHECK(vkMapMemory(a.dev, a.ibMem, 0, isize, 0, &p), "map index buffer");
    memcpy(p, a.mesh.indices.data(), (size_t)isize);
    vkUnmapMemory(a.dev, a.ibMem);
    a.indexCount = (uint32_t)a.mesh.indices.size();
    LOG("[stage] model loaded %zu verts / %u tris (%u src positions, %u src faces, %u degenerate), %.1f MiB VB",
        a.mesh.vertices.size(), a.mesh.srcPositions, a.mesh.triangleCount(), a.mesh.srcFaces,
        a.mesh.degenerate, vsize / 1048576.0);
    return true;
}

// Uploads one DDS into an image + view + sampler. Used for the single model
// path and once per scene-pool model.
static bool uploadOneTexture(App& a, const DdsImage& d, VkImage& img, VkDeviceMemory& mem,
                             VkImageView& view, VkSampler& samp, uint32_t* levelsOut) {
    uint32_t w = d.width, h = d.height, levels = d.mipLevels;
    VkImageCreateInfo ci{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    ci.imageType = VK_IMAGE_TYPE_2D;
    ci.format = d.format;
    ci.extent = {w, h, 1};
    ci.mipLevels = levels;
    ci.arrayLayers = 1;
    ci.samples = VK_SAMPLE_COUNT_1_BIT;
    ci.tiling = VK_IMAGE_TILING_OPTIMAL;
    ci.usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    ci.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    VK_CHECK(vkCreateImage(a.dev, &ci, nullptr, &img), "vkCreateImage(texture)");
    VkMemoryRequirements req;
    vkGetImageMemoryRequirements(a.dev, img, &req);
    VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = findMemoryType(a.phys, req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VK_CHECK(vkAllocateMemory(a.dev, &ai, nullptr, &mem), "vkAllocateMemory(texture)");
    VK_CHECK(vkBindImageMemory(a.dev, img, mem, 0), "vkBindImageMemory(texture)");

    VkBuffer stageBuf = VK_NULL_HANDLE;
    VkDeviceMemory stageMem = VK_NULL_HANDLE;
    if (!createBuffer(a, d.totalBytes, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, stageBuf,
                      stageMem))
        return false;
    void* p = nullptr;
    VK_CHECK(vkMapMemory(a.dev, stageMem, 0, d.totalBytes, 0, &p), "map staging");
    size_t off = 0;
    for (auto& m : d.mips) {
        memcpy((uint8_t*)p + off, m.data(), m.size());
        off += m.size();
    }
    vkUnmapMemory(a.dev, stageMem);

    VkCommandBuffer cb = a.cmd;
    VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(cb, &bi);
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    b.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.image = img;
    b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, 1};
    b.srcAccessMask = 0;
    b.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr,
                         0, nullptr, 1, &b);

    off = 0;
    uint32_t lw = w, lh = h;
    for (uint32_t l = 0; l < levels; ++l) {
        VkBufferImageCopy c{};
        c.bufferOffset = off;
        c.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, l, 0, 1};
        c.imageExtent = {lw, lh, 1};
        vkCmdCopyBufferToImage(cb, stageBuf, img, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &c);
        off += d.mips[l].size();
        lw = lw > 1 ? lw / 2 : 1;
        lh = lh > 1 ? lh / 2 : 1;
    }
    b.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0,
                         nullptr, 0, nullptr, 1, &b);
    vkEndCommandBuffer(cb);
    VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cb;
    VK_CHECK(vkQueueSubmit(a.queue, 1, &si, VK_NULL_HANDLE), "submit texture upload");
    VK_CHECK(vkQueueWaitIdle(a.queue), "wait texture upload");
    vkDestroyBuffer(a.dev, stageBuf, nullptr);
    vkFreeMemory(a.dev, stageMem, nullptr);

    VkImageViewCreateInfo vi{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
    vi.image = img;
    vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
    vi.format = d.format;
    vi.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, 1};
    VK_CHECK(vkCreateImageView(a.dev, &vi, nullptr, &view), "vkCreateImageView(texture)");

    VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
    sci.magFilter = VK_FILTER_LINEAR;
    sci.minFilter = VK_FILTER_LINEAR;
    sci.mipmapMode = VK_SAMPLER_MIPMAP_MODE_LINEAR;
    sci.addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sci.addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sci.maxLod = (float)(levels - 1);
    sci.maxAnisotropy = 1.0f;
    VK_CHECK(vkCreateSampler(a.dev, &sci, nullptr, &samp), "vkCreateSampler");
    if (levelsOut) *levelsOut = levels;
    return true;
}

static bool uploadTexture(App& a) {
    if (!uploadOneTexture(a, a.texData, a.tex, a.texMem, a.texView, a.sampler, &a.texLevels)) return false;
    LOG("[stage] texture uploaded: %ux%u dxgi=%u vkformat=%d mips=%u %.1f MiB", a.texData.width,
        a.texData.height, a.texData.dxgiFormat, (int)a.texData.format, a.texLevels,
        a.texData.totalBytes / 1048576.0);
    return true;
}


// ---------------------------------------------------------------- swapchain dependents

static void destroySwapchainDependents(App& a) {
    if (a.dev == VK_NULL_HANDLE) return;
    if (a.framebuffer) vkDestroyFramebuffer(a.dev, a.framebuffer, nullptr);
    a.framebuffer = VK_NULL_HANDLE;
    if (a.colorView) vkDestroyImageView(a.dev, a.colorView, nullptr);
    a.colorView = VK_NULL_HANDLE;
    if (a.color) vkDestroyImage(a.dev, a.color, nullptr);
    a.color = VK_NULL_HANDLE;
    if (a.colorMem) vkFreeMemory(a.dev, a.colorMem, nullptr);
    a.colorMem = VK_NULL_HANDLE;
    if (a.depthView) vkDestroyImageView(a.dev, a.depthView, nullptr);
    a.depthView = VK_NULL_HANDLE;
    if (a.depth) vkDestroyImage(a.dev, a.depth, nullptr);
    a.depth = VK_NULL_HANDLE;
    if (a.depthMem) vkFreeMemory(a.dev, a.depthMem, nullptr);
    a.depthMem = VK_NULL_HANDLE;
    for (auto v : a.swViews)
        if (v) vkDestroyImageView(a.dev, v, nullptr);
    a.swViews.clear();
    a.swImages.clear();
    if (a.swapchain) vkDestroySwapchainKHR(a.dev, a.swapchain, nullptr);
    a.swapchain = VK_NULL_HANDLE;
}

static bool createSwapchainDependents(App& a) {
    if (!createImage2D(a, a.extent.width, a.extent.height, a.swFormat,
                       VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
                       VK_IMAGE_ASPECT_COLOR_BIT, a.color, a.colorMem, a.colorView))
        return false;
    if (a.readback) {
        vkUnmapMemory(a.dev, a.readbackMem);
        vkDestroyBuffer(a.dev, a.readback, nullptr);
        vkFreeMemory(a.dev, a.readbackMem, nullptr);
        a.readback = VK_NULL_HANDLE;
        a.readbackMem = VK_NULL_HANDLE;
        a.readbackMap = nullptr;
    }
    a.readbackSize = (VkDeviceSize)a.extent.width * a.extent.height * 4;
    if (!createBuffer(a, a.readbackSize, VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                      a.readback, a.readbackMem))
        return false;
    VK_CHECK(vkMapMemory(a.dev, a.readbackMem, 0, a.readbackSize, 0, &a.readbackMap), "map readback");
    if (!createImage2D(a, a.extent.width, a.extent.height, g_depthFormat,
                       VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT, VK_IMAGE_ASPECT_DEPTH_BIT, a.depth,
                       a.depthMem, a.depthView))
        return false;
    VkImageView views[2] = {a.colorView, a.depthView};
    VkFramebufferCreateInfo fi{VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO};
    fi.renderPass = a.renderPass;
    fi.attachmentCount = 2;
    fi.pAttachments = views;
    fi.width = a.extent.width;
    fi.height = a.extent.height;
    fi.layers = 1;
    VK_CHECK(vkCreateFramebuffer(a.dev, &fi, nullptr, &a.framebuffer), "vkCreateFramebuffer");
    return true;
}

// ---------------------------------------------------------------- game shader runtime

// Xbox virtual addresses we chose inside the heap. The shader adds the heap
// base to these itself, so they are also byte offsets into the heap buffer.
static const uint32_t kVaTsharpBase = 0x40000; // one T# per pool model, after the code blobs
static const uint32_t kVaTsharpStride = 0x40;  // 32-byte T#, 0x40-aligned: ~950 models fit
static const uint32_t kVaVsCode = 0x10000;
static const uint32_t kVaPsCode = 0x20000;
static const VkDeviceSize kHeapSize = 4u << 20;

static bool createHeap(App& a) {
    VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    bi.size = kHeapSize;
    bi.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VK_CHECK(vkCreateBuffer(a.dev, &bi, nullptr, &a.heap), "vkCreateBuffer(heap)");
    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(a.dev, a.heap, &req);
    VkMemoryAllocateFlagsInfo afi{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO};
    afi.flags = VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT;
    VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    ai.pNext = &afi;
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = findMemoryType(a.phys, req.memoryTypeBits,
                                        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                            VK_MEMORY_PROPERTY_HOST_COHERENT_BIT |
                                            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (ai.memoryTypeIndex == UINT32_MAX) {
        LOG("[fatal] no host-visible device-local memory for the address heap");
        return false;
    }
    VK_CHECK(vkAllocateMemory(a.dev, &ai, nullptr, &a.heapMem), "vkAllocateMemory(heap)");
    VK_CHECK(vkBindBufferMemory(a.dev, a.heap, a.heapMem, 0), "vkBindBufferMemory(heap)");
    VkBufferDeviceAddressInfo bdi{VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO};
    bdi.buffer = a.heap;
    a.heapBda = vkGetBufferDeviceAddress(a.dev, &bdi);
    VK_CHECK(vkMapMemory(a.dev, a.heapMem, 0, kHeapSize, 0, (void**)&a.heapMap), "map heap");
    memset(a.heapMap, 0, (size_t)kHeapSize);
    LOG("[stage] heap: %llu KiB at BDA 0x%llx (buffer offsets == Xbox VAs)",
        (unsigned long long)(kHeapSize / 1024), (unsigned long long)a.heapBda);

    // Upload each shader's FSSM blob at its chosen code VA; the value is what
    // dwords 34-35 (code base) carry.
    struct Blob { const char* file; uint32_t va; } blobs[2] = {
        {"vs_passthrough.fssm", kVaVsCode}, {"ps_passthrough_copy.fssm", kVaPsCode}};
    for (auto& b : blobs) {
        std::vector<uint8_t> code;
        std::string path = exeDir() + "\\shaders\\gs\\" + b.file;
        if (!readFile(path, code)) {
            LOG("[fatal] cannot read FSSM blob %s", path.c_str());
            return false;
        }
        if (b.va + code.size() > kHeapSize) {
            LOG("[fatal] FSSM blob does not fit the heap");
            return false;
        }
        memcpy(a.heapMap + b.va, code.data(), code.size());
        LOG("[stage] FSSM %s (%zu B) uploaded at heap VA 0x%x", b.file, code.size(), b.va);
    }
    return true;
}

static uint32_t fnv1a(const uint32_t* key) {
    uint32_t h = 2166136261u;
    for (int i = 0; i < 8; ++i) {
        h ^= key[i];
        h *= 16777619u;
    }
    return h;
}

// Insert one 8-dword key into the descriptor hash table (exactly the shader's
// algorithm: FNV-1a, mask, 8 linear probes, entries of {key[8], index, pad}).
static void hashInsert(App& a, const uint32_t* key, uint32_t index) {
    uint32_t slot = fnv1a(key) & a.hashMask;
    for (int i = 0; i < 8; ++i) {
        uint32_t* e = a.hashMap + 1 + slot * 10;
        bool empty = true;
        for (int k = 0; k < 8; ++k)
            if (e[k]) empty = false;
        if (empty || memcmp(e, key, 32) == 0) {
            memcpy(e, key, 32);
            e[8] = index;
            e[9] = 0;
            LOG("[stage] hash insert %08x %08x ... -> index %u at slot %u", key[0], key[1], index,
                slot);
            return;
        }
        slot = (slot + 1) & a.hashMask;
    }
    LOG("[warn] hash table full for key %08x", key[0]);
}

static bool createHashTable(App& a) {
    VkDeviceSize bytes = (VkDeviceSize)(a.hashMask + 1) * 10 * 4 + 4;
    if (!createBuffer(a, bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                      a.hashBuf, a.hashMem))
        return false;
    VK_CHECK(vkMapMemory(a.dev, a.hashMem, 0, bytes, 0, (void**)&a.hashMap), "map hash table");
    memset(a.hashMap, 0, (size_t)bytes);
    a.hashMap[0] = a.hashMask;

    // One T# per pool model at VA 0x1000 + i*0x100, each inserted against its
    // own image index (1 + i). The PS only hashes the T#, so the field values
    // stay cosmetic; the hash is what selects the texture.
    if (a.pool.empty()) {
        LOG("[fatal] empty model pool");
        return false;
    }
    a.modelVa.assign(a.pool.size(), 0);
    a.modelImg.resize(a.pool.size());
    for (size_t i = 0; i < a.pool.size(); ++i) {
        uint32_t va = kVaTsharpBase + (uint32_t)i * kVaTsharpStride;
        if ((VkDeviceSize)va + 32 + kVaTsharpStride > kHeapSize) {
            LOG("[fatal] too many pool models for the T# VA range");
            return false;
        }
        uint32_t tsharp[8] = {0x00003000, 0x00000000, 0x00200000, (uint32_t)(0x14800600u + i),
                              0x00000200, 0xADD20000, 0x00000000, 0x00000000};
        memcpy(a.heapMap + va, tsharp, sizeof(tsharp));
        uint32_t img = a.modelImg[i] ? a.modelImg[i] : 1;
        if (img >= kBindSlotCount) img = 1;
        hashInsert(a, tsharp, img);
        a.modelVa[i] = va;
        a.modelImg[i] = img;
    }
    // s8/s9 = Xbox VA of the *first* model's T#; it is overwritten per draw.
    uint64_t tva = a.modelVa[0];
    memcpy(a.push + 8 * 4, &tva, 8);
    // dwords 32-33 heap base (device address), 34-35 code base (Xbox VA).
    memcpy(a.push + 32 * 4, &a.heapBda, 8);
    uint64_t codeva = kVaPsCode;
    memcpy(a.push + 34 * 4, &codeva, 8);

    // The shader's literal S# is one fixed key: all models share sampler 1.
    uint32_t literalS[] = {0x92, 0xC00000, 0x14500000, 0, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF,
                           0xFFFFFFFF};
    hashInsert(a, literalS, a.shaderImage); // sampler index 1
    if (a.hashEmpty) {
        memset(a.hashMap + 1, 0, (size_t)(a.hashMask + 1) * 10 * 4);
        a.hashMap[0] = 0;
        LOG("[dbg] hash table emptied: mask 0, every lookup misses to index 0");
    }
    return true;
}

// 4x4 magenta/black checker: index 0 of every array is the miss fallback, so a
// hash miss is unmistakable in the PNG.
static bool createFallback(App& a) {
    createImage2D(a, 4, 4, VK_FORMAT_R8G8B8A8_UNORM, VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                  VK_IMAGE_ASPECT_COLOR_BIT, a.fbTex, a.fbTexMem, a.fbTexView);
    VkBuffer sb = VK_NULL_HANDLE;
    VkDeviceMemory sm = VK_NULL_HANDLE;
    if (!createBuffer(a, 64, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, sb, sm))
        return false;
    uint8_t* p = nullptr;
    VK_CHECK(vkMapMemory(a.dev, sm, 0, 64, 0, (void**)&p), "map fallback staging");
    for (int i = 0; i < 16; ++i) {
        bool odd = ((i & 1) ^ ((i >> 2) & 1)) != 0;
        p[i * 4 + 0] = odd ? 255 : 0;
        p[i * 4 + 1] = odd ? 0 : 255;
        p[i * 4 + 2] = odd ? 255 : 0;
        p[i * 4 + 3] = 255;
    }
    vkUnmapMemory(a.dev, sm);

    VkCommandBuffer cb = a.cmd;
    VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(cb, &bi);
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.image = a.fbTex;
    b.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    b.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    b.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0,
                         nullptr, 0, nullptr, 1, &b);
    VkBufferImageCopy c{};
    c.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    c.imageExtent = {4, 4, 1};
    vkCmdCopyBufferToImage(cb, sb, a.fbTex, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &c);
    b.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0,
                         nullptr, 0, nullptr, 1, &b);
    vkEndCommandBuffer(cb);
    VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cb;
    VK_CHECK(vkQueueSubmit(a.queue, 1, &si, VK_NULL_HANDLE), "submit fallback upload");
    VK_CHECK(vkQueueWaitIdle(a.queue), "wait fallback upload");
    vkDestroyBuffer(a.dev, sb, nullptr);
    vkFreeMemory(a.dev, sm, nullptr);

    VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
    sci.magFilter = VK_FILTER_NEAREST;
    sci.minFilter = VK_FILTER_NEAREST;
    sci.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    sci.maxLod = 0.0f;
    VK_CHECK(vkCreateSampler(a.dev, &sci, nullptr, &a.fbSampler), "vkCreateSampler(fallback)");
    LOG("[stage] fallback texture/sampler at index 0");
    return true;
}

static bool writeDescriptors(App& a) {
    // Every slot is written: a non-uniform (per-lane) descriptor fetch into a
    // partially bound array faults on this driver, so the real bindings sit at
    // their true indices (0 = fallback, 1..N = pool models) and the rest are
    // duplicates of the fallback.
    static VkDescriptorImageInfo imgs[kBindSlotCount];
    static VkDescriptorImageInfo sams[kBindSlotCount];
    size_t realCount = a.modelTexView.size();
    for (uint32_t i = 0; i < kBindSlotCount; ++i) {
        bool real = (i >= 1 && i <= realCount);
        VkImageView view = real ? a.modelTexView[i - 1] : a.fbTexView;
        VkSampler samp = real ? a.modelSamp[i - 1] : a.fbSampler;
        imgs[i] = {VK_NULL_HANDLE, view, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL};
        sams[i] = {samp, VK_NULL_HANDLE, VK_IMAGE_LAYOUT_UNDEFINED};
    }
    VkDescriptorBufferInfo dbi{a.hashBuf, 0, VK_WHOLE_SIZE};
    VkWriteDescriptorSet w[3]{};
    for (int i = 0; i < 3; ++i) {
        w[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        w[i].dstSet = a.descSet;
    }
    w[0].dstBinding = 0;
    w[0].descriptorCount = kBindSlotCount;
    w[0].descriptorType = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
    w[0].pImageInfo = imgs;
    w[1].dstBinding = 1;
    w[1].descriptorCount = kBindSlotCount;
    w[1].descriptorType = VK_DESCRIPTOR_TYPE_SAMPLER;
    w[1].pImageInfo = sams;
    w[2].dstBinding = 2;
    w[2].descriptorCount = 1;
    w[2].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    w[2].pBufferInfo = &dbi;
    vkUpdateDescriptorSets(a.dev, 3, w, 0, nullptr);
    LOG("[stage] descriptors written: all %u slots (index 0 = fallback, index 1 = game texture/sampler), "
        "binding 2 = hash table", kBindSlotCount);
    return true;
}


// Synthetic 8x8 single-mip RGBA8 texture, used to test the sample path without
// the real DDS's 12 mips / block compression.
static bool uploadSynthTexture(App& a) {
    const uint32_t w = 8, h = 8;
    createImage2D(a, w, h, VK_FORMAT_R8G8B8A8_UNORM,
                  VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                  VK_IMAGE_ASPECT_COLOR_BIT, a.tex, a.texMem, a.texView);
    VkBuffer sb = VK_NULL_HANDLE;
    VkDeviceMemory sm = VK_NULL_HANDLE;
    if (!createBuffer(a, w * h * 4, VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, sb, sm))
        return false;
    uint8_t* p = nullptr;
    VK_CHECK(vkMapMemory(a.dev, sm, 0, w * h * 4, 0, (void**)&p), "map synth staging");
    for (uint32_t y = 0; y < h; ++y)
        for (uint32_t x = 0; x < w; ++x) {
            uint8_t* t = p + (y * w + x) * 4;
            t[0] = (uint8_t)(x * 32);
            t[1] = (uint8_t)(y * 32);
            t[2] = 128;
            t[3] = 255;
        }
    vkUnmapMemory(a.dev, sm);
    VkCommandBuffer cb = a.cmd;
    VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(cb, &bi);
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.image = a.tex;
    b.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    b.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.srcQueueFamilyIndex = b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    b.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 0,
                         nullptr, 1, &b);
    VkBufferImageCopy c{};
    c.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    c.imageExtent = {w, h, 1};
    vkCmdCopyBufferToImage(cb, sb, a.tex, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &c);
    b.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    b.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    b.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    b.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr,
                         0, nullptr, 1, &b);
    vkEndCommandBuffer(cb);
    VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cb;
    VK_CHECK(vkQueueSubmit(a.queue, 1, &si, VK_NULL_HANDLE), "submit synth texture");
    VK_CHECK(vkQueueWaitIdle(a.queue), "wait synth texture");
    vkDestroyBuffer(a.dev, sb, nullptr);
    vkFreeMemory(a.dev, sm, nullptr);
    VkSamplerCreateInfo sci{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
    sci.magFilter = VK_FILTER_NEAREST;
    sci.minFilter = VK_FILTER_NEAREST;
    sci.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    sci.addressModeU = sci.addressModeV = sci.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    VK_CHECK(vkCreateSampler(a.dev, &sci, nullptr, &a.sampler), "vkCreateSampler(synth)");
    a.texLevels = 1;
    LOG("[stage] synth 8x8 single-mip texture uploaded");
    return true;
}

// Representative model pool. Only ~0.18% of the archetype hashes resolve to a
// name, so exports cannot be chosen per instance; these six are picked only for
// being cheap and visually distinct. Archetype hash -> pool slot is a modulo.
static const char* kDefaultPool[] = {
    "w_sr_shrewsbury_01_mag_02._ft_at_0000000019A2E010.obj",
    "w_pi_fairview_01_barrel_01._dr_at_0000000013029010.obj",
    "w_me_golfclub_01_hi._dr_at_0000000012D22010.obj",
    "w_sports_football_01_ball_01_dmg._ft_at_0000000019509010.obj",
    "w_lr_flaregun_01_hi._dr_at_0000000012C9D010.obj",
    "w_pi_scorpio_01_slide_03._ft_at_0000000017ADA010.obj",
};
static const char* kTexDir =
    "\\..\\work\\assets\\textures\\textures\\dictionary_at_0000000002263010\\";
static const char* kDefaultTex[] = {
    "057_ped_tint_vstation_master4.dds", "071_fog2dnoise512.dds",
    "109_cloudmap_4_hurricaneclouds_b.dds", "012_water_foam_height.dds",
    "055_fogbaseheightmap.dds", "023_ped_tint_garment_clean.dds",
};

static void splitComma(const std::string& s, std::vector<std::string>& out) {
    size_t start = 0;
    while (start <= s.size()) {
        size_t c = s.find(',', start);
        if (c == std::string::npos) c = s.size();
        std::string t = s.substr(start, c - start);
        if (!t.empty()) out.push_back(t);
        start = c + 1;
    }
}

// A tessellated quad in the XZ plane (z up), CW seen from +z, UV repeating.
// Used for the synthetic road/sidewalk so the scene has a place to stand.
//
// It has to be tessellated: VS_main pins clip w to 1, so the perspective divide
// happens on the CPU and a vertex behind the eye is unusable. A two-triangle
// ground plane centred on the camera therefore collapses to a sliver — with
// 16-unit cells the near cells are always in front.
static Mesh makePlane(float sx, float sy, float uvRepX, float uvRepY) {
    const float cell = 16.0f;
    int nx = std::max(1, (int)(sx / cell));
    int ny = std::max(1, (int)(sy / cell));
    Mesh m;
    Vec3 n(0, 0, 1);
    float hx = sx * 0.5f, hy = sy * 0.5f;
    for (int j = 0; j <= ny; ++j) {
        float v = (float)j / (float)ny;
        for (int i = 0; i <= nx; ++i) {
            float u = (float)i / (float)nx;
            m.vertices.push_back({Vec3(-hx + u * sx, -hy + v * sy, 0), n, u * uvRepX, v * uvRepY});
        }
    }
    for (int j = 0; j < ny; ++j) {
        for (int i = 0; i < nx; ++i) {
            uint32_t a = (uint32_t)(j * (nx + 1) + i);
            uint32_t b = a + 1;
            uint32_t c = a + (uint32_t)(nx + 1);
            uint32_t d = c + 1;
            m.indices.insert(m.indices.end(), {a, c, b, b, c, d}); // CW from +z
        }
    }
    m.bmin = Vec3(-hx, -hy, 0);
    m.bmax = Vec3(hx, hy, 0);
    m.radius = 0.5f * std::sqrt(sx * sx + sy * sy);
    return m;
}

// Procedural texture for the synthetic ground: mottled grey asphalt. DdsImage is
// just a format + tightly packed mips, so this goes through the same upload path
// as a real DDS without needing a file.
static void makeGroundTexture(DdsImage& d, uint32_t seed, uint8_t base, uint32_t size) {
    d.width = d.height = size;
    d.mipLevels = 1;
    d.format = VK_FORMAT_R8G8B8A8_UNORM;
    d.srgb = false;
    d.dxgiFormat = 28;
    std::vector<uint8_t> px((size_t)size * size * 4);
    uint32_t s = seed | 1u;
    for (size_t i = 0; i < (size_t)size * size; ++i) {
        s ^= s << 13;
        s ^= s >> 17;
        s ^= s << 5;
        int v = (int)base + (int)(s % 24) - 12;
        v = v < 0 ? 0 : (v > 255 ? 255 : v);
        px[i * 4 + 0] = (uint8_t)v;
        px[i * 4 + 1] = (uint8_t)v;
        px[i * 4 + 2] = (uint8_t)(v + 3 > 255 ? 255 : v + 3);
        px[i * 4 + 3] = 255;
    }
    d.mips.clear();
    d.mips.push_back(std::move(px));
    d.totalBytes = (size_t)size * size * 4;
}

// Loads the scene file and the model pool. If the scene carries a per-instance
// "model" path (M4 block scenes do), every distinct path is loaded once and the
// instance points at it; otherwise the M3 behaviour (hash % pool) is kept.
// World matrices, the per-model sort and the dynamic buffer budget follow.
static bool setupScene(App& a, const Args& args) {
    std::string dir = exeDir();
    std::string err;
    if (!loadScene(args.scene, args.limit, a.scene, err)) {
        LOG("[fatal] scene load failed: %s (%s)", err.c_str(), args.scene.c_str());
        return false;
    }
    LOG("[scene] %s: %zu instances, %u distinct hashes, rot identity on %u, scale identity on %u",
        args.scene.c_str(), a.scene.instances.size(), a.scene.distinctHashes, a.scene.identityRot,
        a.scene.identityScale);
    LOG("[scene] bounds x %.1f..%.1f  y %.1f..%.1f  z %.2f..%.2f  centroid %.1f %.1f %.1f", a.scene.lo.x,
        a.scene.hi.x, a.scene.lo.y, a.scene.hi.y, a.scene.lo.z, a.scene.hi.z, a.scene.centroid.x,
        a.scene.centroid.y, a.scene.centroid.z);

    // Distinct model paths, in first-seen order.
    std::vector<std::string> names;
    std::vector<int> pathSlot;
    {
        std::vector<std::pair<std::string, int>> seen;
        auto slotFor = [&](const std::string& p) -> int {
            for (auto& s : seen)
                if (s.first == p) return s.second;
            int idx = (int)seen.size();
            seen.emplace_back(p, idx);
            names.push_back(p);
            return idx;
        };
        bool anyModel = false;
        for (auto& in : a.scene.instances)
            if (!in.modelPath.empty()) anyModel = true;
        if (anyModel) {
            for (auto& in : a.scene.instances) {
                if (in.modelPath.empty()) {
                    in.modelPath = a.scene.instances[0].modelPath; // tolerate a missing field
                }
                in.model = slotFor(in.modelPath);
            }
            LOG("[scene] per-instance models: %zu distinct file(s)", names.size());
        } else {
            std::vector<std::string> pool;
            if (args.pool.empty()) {
                for (const char* n : kDefaultPool) pool.push_back(dir + "\\..\\work\\assets\\data\\models\\" + n);
            } else {
                splitComma(args.pool, pool);
            }
            if (pool.empty()) {
                LOG("[fatal] empty model pool");
                return false;
            }
            names = pool;
            size_t nModels = names.size();
            LOG("[scene] no per-instance model field: pool of %zu, hash %% pool", nModels);
            for (auto& in : a.scene.instances) in.model = (int)(in.hash % nModels);
        }
    }

    // Synthetic ground: appended as three extra models (terrain, road,
    // sidewalk), placed through the scene centre at ground level. Only when
    // asked for (--ground-plane), so the pure data render stays pure.
    int terrainModel = -1, roadModel = -1, walkModel = -1;
    float gsx = 0.0f, gsy = 0.0f;
    if (args.groundPlane) {
        float cx = a.scene.centroid.x, cy = a.scene.centroid.y;
        gsx = std::max(120.0f, a.scene.extentX + 90.0f);
        gsy = std::max(120.0f, a.scene.extentY + 90.0f);
        terrainModel = (int)names.size();
        names.push_back("<terrain>");
        roadModel = (int)names.size();
        names.push_back("<road>");
        walkModel = (int)names.size();
        names.push_back("<walk>");
        auto addGround = [&](int model, float px, float py, float z) {
            SceneInstance in;
            in.pos = Vec3(px, py, z);
            in.model = model;
            a.scene.instances.push_back(in);
        };
        addGround(roadModel, cx, cy, -0.05f);   // 14-unit carriageway
        addGround(terrainModel, cx, cy, -0.12f); // wider ground under everything
        addGround(walkModel, cx - 10.0f, cy, 0.12f);
        addGround(walkModel, cx + 10.0f, cy, 0.12f);
        LOG("[scene] ground plane added at %.1f %.1f (%.0f x %.0f): road 14 wide, 6-unit sidewalks", cx,
            cy, gsx, gsy);
    }

    a.pool.resize(names.size());
    size_t nLoaded = 0;
    for (size_t i = 0; i < names.size(); ++i) {
        if (args.groundPlane && (int)i == roadModel) {
            a.pool[i] = makePlane(14.0f, gsy, 2.0f, 120.0f);
            ++nLoaded;
            continue;
        }
        if (args.groundPlane && (int)i == terrainModel) {
            a.pool[i] = makePlane(gsx, gsy, 40.0f, 160.0f);
            ++nLoaded;
            continue;
        }
        if (args.groundPlane && (int)i == walkModel) {
            a.pool[i] = makePlane(6.0f, gsy, 2.0f, 160.0f);
            ++nLoaded;
            continue;
        }
        if (!loadObj(names[i], a.pool[i], err, args.normalize, args.ground)) {
            LOG("[warn] model %zu failed (%s): %s", i, err.c_str(), names[i].c_str());
            a.pool[i] = Mesh();
            continue;
        }
        ++nLoaded;
        if (i < 3 || args.stats)
            LOG("[scene] model[%zu] %s: %u tris, bbox %.2f,%.2f,%.2f..%.2f,%.2f,%.2f r=%.2f", i,
                names[i].c_str(), a.pool[i].triangleCount(), a.pool[i].bmin.x, a.pool[i].bmin.y,
                a.pool[i].bmin.z, a.pool[i].bmax.x, a.pool[i].bmax.y, a.pool[i].bmax.z,
                a.pool[i].radius);
    }
    if (!nLoaded) {
        LOG("[fatal] no model loaded");
        return false;
    }
    LOG("[scene] %zu of %zu model(s) loaded (normalize=%d ground=%d)", nLoaded, names.size(),
        (int)args.normalize, (int)args.ground);

    // Ground instances were appended after the sort key was fixed, so the sort
    // below covers them too; their model index is the highest, which is fine.

    size_t nModels = a.pool.size();
    uint64_t totalVerts = 0, totalIndices = 0;
    uint32_t dropped = 0;
    for (auto& in : a.scene.instances) {
        if (in.model < 0 || (size_t)in.model >= nModels || a.pool[in.model].indices.empty()) {
            ++dropped;
            continue;
        }
        if (args.spinDeg != 0.0f) {
            // Same axis/angle applied on top of the game quaternion, purely as
            // proof the rotation path works (the data's quaternions are identity).
            float ha = (args.spinDeg * 3.14159265f / 180.0f) * 0.5f;
            Quat yaw{0.0f, std::sin(ha), 0.0f, std::cos(ha)};
            Quat r = in.rot;
            Quat outq{r.w * yaw.x + r.x * yaw.w + r.y * yaw.z - r.z * yaw.y,
                      r.w * yaw.y - r.x * yaw.z + r.y * yaw.w + r.z * yaw.x,
                      r.w * yaw.z + r.x * yaw.y - r.y * yaw.x + r.z * yaw.w,
                      r.w * yaw.w - r.x * yaw.x - r.y * yaw.y - r.z * yaw.z};
            in.rot = outq;
        }
        in.world = composeInstance(in, args.displayScale);
        const Mesh& m = a.pool[(size_t)in.model];
        totalVerts += m.vertices.size();
        totalIndices += m.indices.size();
    }
    if (dropped) LOG("[scene] %u instance(s) dropped: model missing or empty", dropped);
    std::stable_sort(a.scene.instances.begin(), a.scene.instances.end(),
                     [](const SceneInstance& l, const SceneInstance& r) { return l.model < r.model; });

    a.dynVboBytes = (VkDeviceSize)totalVerts * sizeof(MeshVertex);
    a.dynIboBytes = (VkDeviceSize)totalIndices * 4;
    LOG("[scene] scene buffer budget %llu verts / %llu indices (%.1f MiB VB, %.1f MiB IB)",
        (unsigned long long)totalVerts, (unsigned long long)totalIndices, a.dynVboBytes / 1048576.0,
        a.dynIboBytes / 1048576.0);

    if (!createBuffer(a, a.dynVboBytes,
                      VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, a.dynVbo,
                      a.dynVboMem))
        return false;
    if (!createBuffer(a, a.dynIboBytes, VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                      VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT, a.dynIbo,
                      a.dynIboMem))
        return false;
    VK_CHECK(vkMapMemory(a.dev, a.dynVboMem, 0, a.dynVboBytes, 0, (void**)&a.dynVboMap), "map scene VB");
    VK_CHECK(vkMapMemory(a.dev, a.dynIboMem, 0, a.dynIboBytes, 0, (void**)&a.dynIboMap), "map scene IB");

    // A handful of shared textures, cycled per model: the exports carry no
    // material binding, so per-model textures would be a lie anyway.
    const size_t nTex = sizeof(kDefaultTex) / sizeof(*kDefaultTex) + (args.groundPlane ? 1u : 0u);
    a.modelTex.resize(nTex);
    a.modelTexMem.resize(nTex);
    a.modelTexView.resize(nTex);
    a.modelSamp.resize(nTex);
    for (size_t i = 0; i < nTex; ++i) {
        DdsImage d;
        bool ok = false;
        if (args.groundPlane && i + 1 == nTex) {
            makeGroundTexture(d, 0x5eed1234u, 74, 64);
            ok = true;
            LOG("[scene] texture %zu = procedural asphalt", i);
        } else {
            std::string texPath = dir + kTexDir + kDefaultTex[i % (sizeof(kDefaultTex) / sizeof(*kDefaultTex))];
            ok = loadDds(texPath, d, err);
            if (ok) LOG("[scene] texture %zu = %s", i, texPath.c_str());
            else LOG("[warn] texture %zu failed (%s): %s", i, err.c_str(), texPath.c_str());
        }
        if (ok) uploadOneTexture(a, d, a.modelTex[i], a.modelTexMem[i], a.modelTexView[i], a.modelSamp[i], nullptr);
    }
    // Model -> descriptor image index. Real models cycle the DDS set; the three
    // synthetic ground models share the procedural asphalt at the last index.
    a.modelImg.assign(nModels, 1);
    for (size_t i = 0; i < nModels; ++i) {
        if (args.groundPlane && nModels >= 3 && i >= nModels - 3)
            a.modelImg[i] = (uint32_t)nTex;
        else
            a.modelImg[i] = 1 + (uint32_t)(i % (sizeof(kDefaultTex) / sizeof(*kDefaultTex)));
    }
    a.sceneMode = true;
    return true;
}

static bool createGsResources(App& a) {
    if (!createHeap(a)) return false;
    if (!createHashTable(a)) return false;
    if (!createFallback(a)) return false;
    if (!writeDescriptors(a)) return false;
    LOG("[stage] push block: %zu T# VAs from 0x%x, heap base (BDA) 0x%llx, code base VA 0x%x",
        a.pool.size(), kVaTsharpBase, (unsigned long long)a.heapBda, kVaPsCode);
    return true;
}

// ---------------------------------------------------------------- frame

static void imageBarrier(VkCommandBuffer cb, VkImage img, VkImageLayout from, VkImageLayout to,
                         VkAccessFlags src, VkAccessFlags dst, VkPipelineStageFlags srcStage,
                         VkPipelineStageFlags dstStage) {
    VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    b.oldLayout = from;
    b.newLayout = to;
    b.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    b.image = img;
    b.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    b.srcAccessMask = src;
    b.dstAccessMask = dst;
    vkCmdPipelineBarrier(cb, srcStage, dstStage, 0, 0, nullptr, 0, nullptr, 1, &b);
}

// ---------------------------------------------------------------- M3 scene

static Vec3 parseVec3(const std::string& s, const Vec3& def) {
    float v[3] = {0, 0, 0};
    int n = 0;
    const char* p = s.c_str();
    while (*p && n < 3) {
        char* endp = nullptr;
        float f = strtof(p, &endp);
        if (endp == p) break;
        v[n++] = f;
        p = endp;
        while (*p == ',' || *p == ' ') ++p;
    }
    return n == 3 ? Vec3(v[0], v[1], v[2]) : def;
}

// Camera: centroid based unless --cam/--look override it. The strip is ~13.5k
// units long and 6 wide, so the presets differ mainly in distance.
static void computeCamera(App& a, const Args& args) {
    Vec3 c = a.scene.focus;
    if (a.userCam) {
        float d = (a.camTarget - a.camEye).length();
        a.camNear = std::max(0.05f, d * 0.01f);
        a.camFar = d * 8.0f + a.scene.extentX;
        return;
    }
    float fe = std::max(a.scene.focusExtent, 30.0f);
    if (args.view == "street") {
        // Street level. The block scenes run along +y with the road on x = 0, so
        // eye height 1.7 m and a look down the street.
        a.camEye = Vec3(c.x, c.y - fe * 0.55f, 1.7f);
        a.camTarget = Vec3(c.x, c.y + std::max(80.0f, fe), 6.0f);
        a.camNear = 0.2f;
        a.camFar = fe * 25.0f + 800.0f;
    } else if (args.view == "block") {
        // Mid-range 3/4 view of the clump.
        float dist = std::clamp(fe * 0.45f, 25.0f, 400.0f);
        a.camEye = c + Vec3(0.0f, dist * 0.55f, dist * 0.84f);
        a.camTarget = c;
        a.camNear = std::max(0.2f, dist * 0.05f);
        a.camFar = dist * 20.0f + fe * 4.0f + 1000.0f;
    } else {
        // Whole clump from above and in front.
        float dist = std::max(fe * 1.1f, 120.0f);
        a.camEye = c + Vec3(0.0f, dist * 0.52f, dist * 0.86f);
        a.camTarget = c;
        a.camNear = std::max(0.5f, dist * 0.02f);
        a.camFar = dist * 8.0f + a.scene.extentX;
    }
    LOG("[scene] camera %s: eye (%.1f %.1f %.1f) -> look (%.1f %.1f %.1f) near %.2f far %.0f (clump %.0f wide)",
        args.view.c_str(), a.camEye.x, a.camEye.y, a.camEye.z, a.camTarget.x, a.camTarget.y,
        a.camTarget.z, a.camNear, a.camFar, fe);
}

// Rebuilds the dynamic vertex/index slabs. One contiguous slab per model, the
// per-instance matrix applied on the CPU, output already in clip space because
// the game VS passes POSITION through untouched.
static void buildSceneGeometry(App& a, const Mat4& viewProj, bool frustumCull) {
    size_t nModels = a.pool.size();
    a.modelDrawOffset.assign(nModels, 0);
    a.modelDrawCount.assign(nModels, 0);
    a.drawnInstances = a.culledInstances = a.drawnTris = a.drawnVerts = a.drawnDraws = 0;
    if (!a.dynVboMap || !a.dynIboMap) return;

    if (a.blitTest) {
        // One giant screen-space triangle straight into the dynamic buffer.
        float tri[3][8] = {{-2, -2, 0.5f, 0, 0, 0, 0, 0},
                           {4, -2, 0.5f, 0, 0, 0, 1, 0},
                           {-2, 4, 0.5f, 0, 0, 0, 0, 1}};
        memcpy(a.dynVboMap, tri, sizeof(tri));
        for (int i = 0; i < 3; ++i) a.dynIboMap[i] = (uint32_t)i;
        a.modelDrawCount[0] = 3;
        a.drawnVerts = 3;
        return;
    }

    float pl[6][4];
    frustumPlanes(viewProj, pl);

    uint32_t vcount = 0, icount = 0;
    for (const auto& in : a.scene.instances) {
        size_t mi = (size_t)in.model;
        if (mi >= nModels) continue;
        const Mesh& mesh = a.pool[mi];
        if (frustumCull && !sphereVisible(pl, in.pos + Vec3(0, 0, 0), instanceRadius(in, mesh.radius, 1.0f) * 1.05f)) {
            ++a.culledInstances;
            continue;
        }
        size_t nv = mesh.vertices.size(), ni = mesh.indices.size();
        if ((VkDeviceSize)(vcount + nv) * sizeof(MeshVertex) > a.dynVboBytes) break;
        if ((VkDeviceSize)(icount + ni) * 4 > a.dynIboBytes) break;

        Mat4 mv = viewProj * in.world;
        const float* s = (const float*)mesh.vertices.data();
        float* d = (float*)(a.dynVboMap + vcount);
        for (size_t k = 0; k < nv; ++k) {
            const float* sp = s + k * 8;
            float* dp = d + k * 8;
            float x = sp[0], y = sp[1], z = sp[2];
            float cx = mv.m[0] * x + mv.m[4] * y + mv.m[8] * z + mv.m[12];
            float cy = mv.m[1] * x + mv.m[5] * y + mv.m[9] * z + mv.m[13];
            float cz = mv.m[2] * x + mv.m[6] * y + mv.m[10] * z + mv.m[14];
            float cw = mv.m[3] * x + mv.m[7] * y + mv.m[11] * z + mv.m[15];
            // vs_main forces the output w to 1, i.e. it treats POSITION as
            // already-normalised device coordinates, so the perspective divide
            // has to happen here. A vertex behind the eye gets pushed to z = -1.
            float iw = cw > 1e-6f ? 1.0f / cw : 0.0f;
            dp[0] = cx * iw;
            dp[1] = cy * iw;
            dp[2] = cw > 1e-6f ? cz * iw : -1.0f;
            dp[3] = 0.0f;
            dp[4] = 0.0f;
            dp[5] = 0.0f;
            dp[6] = sp[6];
            dp[7] = sp[7];
        }
        if (a.modelDrawCount[mi] == 0) a.modelDrawOffset[mi] = icount;
        for (size_t k = 0; k < ni; ++k) a.dynIboMap[icount + k] = (uint32_t)(vcount + mesh.indices[k]);
        a.modelDrawCount[mi] += (uint32_t)ni;
        icount += (uint32_t)ni;
        vcount += (uint32_t)nv;
        ++a.drawnInstances;
        a.drawnTris += mesh.triangleCount();
    }
    a.drawnVerts = vcount;
    if (a.frameIdx == 1) {
        uint32_t m0 = 0;
        while (m0 < nModels && !a.modelDrawCount[m0]) ++m0;
        if (m0 < nModels) {
            const float* f = (const float*)a.dynVboMap;
            LOG("[dbg] model %u: first 3 verts clip (%.3f %.3f %.3f) (%.3f %.3f %.3f) (%.3f %.3f %.3f), "
                "count %u offset %u",
                m0, f[0], f[1], f[2], f[8], f[9], f[10], f[16], f[17], f[18], a.modelDrawCount[m0],
                a.modelDrawOffset[m0]);
            LOG("[dbg] idx first6 %u %u %u %u %u %u (vverts %u)",
                a.dynIboMap[a.modelDrawOffset[m0]], a.dynIboMap[a.modelDrawOffset[m0] + 1],
                a.dynIboMap[a.modelDrawOffset[m0] + 2], a.dynIboMap[a.modelDrawOffset[m0] + 3],
                a.dynIboMap[a.modelDrawOffset[m0] + 4], a.dynIboMap[a.modelDrawOffset[m0] + 5], a.drawnVerts);
            // First visible instance's own position projected with the bare VP, to
            // check the placement really lands in view.
            for (const auto& in : a.scene.instances) {
                Mat4 m = viewProj;
                float x = in.pos.x, y = in.pos.y, z = in.pos.z;
                float cx = m.m[0] * x + m.m[4] * y + m.m[8] * z + m.m[12];
                float cy = m.m[1] * x + m.m[5] * y + m.m[9] * z + m.m[13];
                float cz = m.m[2] * x + m.m[6] * y + m.m[10] * z + m.m[14];
                float cw = m.m[3] * x + m.m[7] * y + m.m[11] * z + m.m[15];
                LOG("[dbg] inst pos (%.1f %.1f %.1f) clip w=%.2f ndc (%.3f %.3f %.3f)", x, y, z, cw,
                    cx / cw, cy / cw, cz / cw);
                break;
            }
        }
    }
}

static bool recordFrame(App& a, const Args& args, uint32_t imageIndex, uint32_t frameIndex,
                        bool capture) {
    VkCommandBuffer cb = a.cmd;
    VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    VK_CHECK(vkBeginCommandBuffer(cb, &bi), "vkBeginCommandBuffer");

    VkImage swImg = a.swImages[imageIndex];
    imageBarrier(cb, swImg, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 0,
                 VK_ACCESS_TRANSFER_WRITE_BIT, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                 VK_PIPELINE_STAGE_TRANSFER_BIT);
    // Offscreen target: UNDEFINED is fine every frame, the clear rewrites all pixels.
    imageBarrier(cb, a.color, VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL, 0,
                 VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                 VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT);

    VkClearValue clears[2];
    clears[0].color = {{0.05f, 0.06f, 0.09f, 1.0f}};
    if (args.sky) clears[0].color = {{0.42f, 0.56f, 0.76f, 1.0f}};
    clears[1].depthStencil = {1.0f, 0};
    VkRenderPassBeginInfo rp{VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO};
    rp.renderPass = a.renderPass;
    rp.framebuffer = a.framebuffer;
    rp.renderArea = {{0, 0}, a.extent};
    rp.clearValueCount = 2;
    rp.pClearValues = clears;
    vkCmdBeginRenderPass(cb, &rp, VK_SUBPASS_CONTENTS_INLINE);

    VkViewport vp{0, 0, (float)a.extent.width, (float)a.extent.height, 0.0f, 1.0f};
    VkRect2D sc{{0, 0}, a.extent};
    vkCmdSetViewport(cb, 0, 1, &vp);
    vkCmdSetScissor(cb, 0, 1, &sc);
    vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, a.pipeline);
    vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_GRAPHICS, a.pipeLayout, 0, 1, &a.descSet, 0, nullptr);

    VkDeviceSize voff = 0;
    if (!a.sceneMode) {
        vkCmdBindVertexBuffers(cb, 0, 1, &a.vbuf, &voff);
        vkCmdBindIndexBuffer(cb, a.ibuf, 0, VK_INDEX_TYPE_UINT32);
    }

    float aspect = (float)a.extent.width / (float)a.extent.height;

    if (a.sceneMode) {
        Mat4 proj = perspective(0.86f, aspect, a.camNear, a.camFar);
        // The data is Z-up (x east, y north, z up), but lookAt is called with
        // up = +y in the M3 code. With up = +y and a view along +y the basis was
        // degenerate (f x up ~ 0), so the camera has to be Z-up here.
        Mat4 view = lookAt(a.camEye, a.camTarget, Vec3(0, 0, 1));
        Mat4 viewProj = proj * view;
        buildSceneGeometry(a, viewProj, !args.noFrustum);

        vkCmdBindVertexBuffers(cb, 0, 1, &a.dynVbo, &voff);
        vkCmdBindIndexBuffer(cb, a.dynIbo, 0, VK_INDEX_TYPE_UINT32);
        // One push + one indexed draw per model that survived culling. The push
        // differs only in s8/s9 (that model's T# VA), so each model samples its
        // own texture through the same bindless hash path.
        uint64_t baseVa = 0;
        memcpy(&baseVa, a.push + 8 * 4, 8);
        for (size_t m = 0; m < a.pool.size(); ++m) {
            if (!a.modelDrawCount[m]) continue;
            uint64_t va = a.modelVa[m];
            memcpy(a.push + 8 * 4, &va, 8);
            vkCmdPushConstants(cb, a.pipeLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                               0, 144, a.push);
            ++a.drawnDraws;
            if (a.blitTest)
                vkCmdDraw(cb, 3, 1, 0, 0);
            else
                vkCmdDrawIndexed(cb, a.modelDrawCount[m], 1, a.modelDrawOffset[m], 0, 0);
            if (a.frameIdx == 1)
                LOG("[dbg] draw model %zu count %u first %u vbo %p ibo %p", m, a.modelDrawCount[m],
                    a.modelDrawOffset[m], (void*)a.dynVbo, (void*)a.dynIbo);
        }
        memcpy(a.push + 8 * 4, &baseVa, 8);
        if (a.reps > 1 && a.frameIdx == 0) LOG("[scene] reps ignored in scene mode");
    } else {
        Mat4 proj = perspective(0.86f, aspect, 0.05f, 20.0f);
        Vec3 eye(0.0f, 0.42f, 1.95f);
        Vec3 target(0.0f, 0.0f, 0.0f);
        Mat4 view = lookAt(eye, target, Vec3(0, 1, 0));
        (void)view;
        // The game VS synthesizes geometry from gl_VertexIndex and builds its own
        // clip-space position, so the whole 144-byte push block goes in as-is and a
        // three-vertex draw covers the target.
        if (a.reps > 1 && a.frameIdx == 0) LOG("[stage] reps ignored by the game-shader path");
        vkCmdPushConstants(cb, a.pipeLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                           0, 144, a.push);
        if (a.meshMode)
            vkCmdDrawIndexed(cb, a.indexCount, 1, 0, 0, 0);
        else
            vkCmdDraw(cb, 3, 1, 0, 0);
    }

    vkCmdEndRenderPass(cb);

    imageBarrier(cb, a.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                 VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT, VK_ACCESS_TRANSFER_READ_BIT,
                 VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT);

    VkImageCopy region{};
    region.srcSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    region.dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
    region.extent = {a.extent.width, a.extent.height, 1};
    vkCmdCopyImage(cb, a.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, swImg,
                   VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);

    if (capture) {
        VkBufferImageCopy bc{};
        bc.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        bc.imageExtent = {a.extent.width, a.extent.height, 1};
        vkCmdCopyImageToBuffer(cb, a.color, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, a.readback, 1, &bc);
    }

    imageBarrier(cb, swImg, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR,
                 VK_ACCESS_TRANSFER_WRITE_BIT, 0, VK_PIPELINE_STAGE_TRANSFER_BIT,
                 VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT);
    VK_CHECK(vkEndCommandBuffer(cb), "vkEndCommandBuffer");
    return true;
}

// ---------------------------------------------------------------- init/teardown

static bool initVulkan(App& a, const Args& args) {
    if (!createInstance(a, args)) return false;
    if (!createSurface(a)) return false;
    if (!pickDevice(a)) return false;
    if (!createSwapchain(a, args)) return false;
    if (!createDescriptorLayout(a)) return false;
    if (!createRenderPass(a)) return false;

    VkCommandPoolCreateInfo pci{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    pci.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pci.queueFamilyIndex = a.queueFamily;
    VK_CHECK(vkCreateCommandPool(a.dev, &pci, nullptr, &a.cmdPool), "vkCreateCommandPool");
    VkCommandBufferAllocateInfo cbi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    cbi.commandPool = a.cmdPool;
    cbi.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cbi.commandBufferCount = 1;
    VK_CHECK(vkAllocateCommandBuffers(a.dev, &cbi, &a.cmd), "vkAllocateCommandBuffers");

    VkFenceCreateInfo fci{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    VK_CHECK(vkCreateFence(a.dev, &fci, nullptr, &a.fence), "vkCreateFence");
    VkSemaphoreCreateInfo sci{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    VK_CHECK(vkCreateSemaphore(a.dev, &sci, nullptr, &a.semAcquire), "vkCreateSemaphore");
    VK_CHECK(vkCreateSemaphore(a.dev, &sci, nullptr, &a.semRender), "vkCreateSemaphore");

    if (!createSwapchainDependents(a)) return false;
    if (!createPipeline(a)) return false;
    if (a.sceneMode) {
        if (!setupScene(a, args)) return false;
    } else {
        if (!uploadMesh(a)) return false;
        if (a.texSynth) {
            if (!uploadSynthTexture(a)) return false;
        } else if (!uploadTexture(a)) {
            return false;
        }
        // The single-model path reuses the pool machinery with one entry.
        a.pool.assign(1, a.mesh);
        a.modelTex.push_back(a.tex);
        a.modelTexMem.push_back(a.texMem);
        a.modelTexView.push_back(a.texView);
        a.modelSamp.push_back(a.sampler);
    }
    if (!createGsResources(a)) return false;
    return true;
}

static void destroyAll(App& a) {
    if (a.dev) vkDeviceWaitIdle(a.dev);
    destroySwapchainDependents(a);
    if (a.dev) {
        if (a.sceneMode) {
            for (auto s : a.modelSamp)
                if (s) vkDestroySampler(a.dev, s, nullptr);
            for (auto v : a.modelTexView)
                if (v) vkDestroyImageView(a.dev, v, nullptr);
            for (auto i : a.modelTex)
                if (i) vkDestroyImage(a.dev, i, nullptr);
            for (auto m : a.modelTexMem)
                if (m) vkFreeMemory(a.dev, m, nullptr);
        }
        if (a.dynVboMap) vkUnmapMemory(a.dev, a.dynVboMem);
        if (a.dynIboMap) vkUnmapMemory(a.dev, a.dynIboMem);
        if (a.dynVbo) vkDestroyBuffer(a.dev, a.dynVbo, nullptr);
        if (a.dynVboMem) vkFreeMemory(a.dev, a.dynVboMem, nullptr);
        if (a.dynIbo) vkDestroyBuffer(a.dev, a.dynIbo, nullptr);
        if (a.dynIboMem) vkFreeMemory(a.dev, a.dynIboMem, nullptr);
        if (a.ubo) vkDestroyBuffer(a.dev, a.ubo, nullptr);
        if (a.uboMem) vkFreeMemory(a.dev, a.uboMem, nullptr);
        if (a.fbSampler) vkDestroySampler(a.dev, a.fbSampler, nullptr);
        if (a.fbTexView) vkDestroyImageView(a.dev, a.fbTexView, nullptr);
        if (a.fbTex) vkDestroyImage(a.dev, a.fbTex, nullptr);
        if (a.fbTexMem) vkFreeMemory(a.dev, a.fbTexMem, nullptr);
        if (a.hashBuf) vkDestroyBuffer(a.dev, a.hashBuf, nullptr);
        if (a.hashMem) vkFreeMemory(a.dev, a.hashMem, nullptr);
        if (a.heap) vkDestroyBuffer(a.dev, a.heap, nullptr);
        if (a.heapMem) vkFreeMemory(a.dev, a.heapMem, nullptr);
        if (a.sampler) vkDestroySampler(a.dev, a.sampler, nullptr);
        if (a.texView) vkDestroyImageView(a.dev, a.texView, nullptr);
        if (a.tex) vkDestroyImage(a.dev, a.tex, nullptr);
        if (a.texMem) vkFreeMemory(a.dev, a.texMem, nullptr);
        if (a.vbuf) vkDestroyBuffer(a.dev, a.vbuf, nullptr);
        if (a.vbMem) vkFreeMemory(a.dev, a.vbMem, nullptr);
        if (a.ibuf) vkDestroyBuffer(a.dev, a.ibuf, nullptr);
        if (a.ibMem) vkFreeMemory(a.dev, a.ibMem, nullptr);
        if (a.readback) vkDestroyBuffer(a.dev, a.readback, nullptr);
        if (a.readbackMem) vkFreeMemory(a.dev, a.readbackMem, nullptr);
        if (a.pipeline) vkDestroyPipeline(a.dev, a.pipeline, nullptr);
        if (a.pipeLayout) vkDestroyPipelineLayout(a.dev, a.pipeLayout, nullptr);
        if (a.renderPass) vkDestroyRenderPass(a.dev, a.renderPass, nullptr);
        if (a.descPool) vkDestroyDescriptorPool(a.dev, a.descPool, nullptr);
        if (a.setLayout) vkDestroyDescriptorSetLayout(a.dev, a.setLayout, nullptr);
        if (a.fence) vkDestroyFence(a.dev, a.fence, nullptr);
        if (a.semAcquire) vkDestroySemaphore(a.dev, a.semAcquire, nullptr);
        if (a.semRender) vkDestroySemaphore(a.dev, a.semRender, nullptr);
        if (a.cmdPool) vkDestroyCommandPool(a.dev, a.cmdPool, nullptr);
        vkDestroyDevice(a.dev, nullptr);
    }
    if (a.surface) vkDestroySurfaceKHR(a.instance, a.surface, nullptr);
    if (a.instance) vkDestroyInstance(a.instance, nullptr);
}

static void writeShot(App& a, const std::string& path) {
    // Swapchain format is B8G8R8A8_UNORM: convert to RGB.
    size_t pixels = (size_t)a.extent.width * a.extent.height;
    std::vector<uint8_t> rgb(pixels * 3);
    const uint8_t* src = (const uint8_t*)a.readbackMap;
    for (size_t i = 0; i < pixels; ++i) {
        rgb[i * 3 + 0] = src[i * 4 + 2];
        rgb[i * 3 + 1] = src[i * 4 + 1];
        rgb[i * 3 + 2] = src[i * 4 + 0];
    }
    if (writePngRgb(path, rgb.data(), a.extent.width, a.extent.height))
        LOG("[stage] screenshot written: %s (%ux%u, %zu bytes RGB)", path.c_str(), a.extent.width,
            a.extent.height, pixels * 3);
    else
        LOG("[warn] screenshot write failed: %s", path.c_str());
}

int main(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        auto next = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                LOG("[warn] %s needs a value", name);
                return nullptr;
            }
            return argv[++i];
        };
        if (s == "--width") { const char* v = next("--width"); if (v) args.width = atoi(v); }
        else if (s == "--height") { const char* v = next("--height"); if (v) args.height = atoi(v); }
        else if (s == "--reps") { const char* v = next("--reps"); if (v) args.reps = atoi(v); }
        else if (s == "--frames") { const char* v = next("--frames"); if (v) args.frames = atoi(v); }
        else if (s == "--warmup") { const char* v = next("--warmup"); if (v) args.warmup = atoi(v); }
        else if (s == "--capture") { const char* v = next("--capture"); if (v) args.captureFrame = atoi(v); }
        else if (s == "--model") { const char* v = next("--model"); if (v) args.model = v; }
        else if (s == "--texture") { const char* v = next("--texture"); if (v) args.texture = v; }
        else if (s == "--shot") { const char* v = next("--shot"); if (v) args.shot = v; }
        else if (s == "--validate") args.validate = true;
        else if (s == "--fs-dbg") args.fsDbg = true;
        else if (s == "--hash-empty") args.hashEmpty = true;
        else if (s == "--ps") { const char* v = next("--ps"); if (v) args.psName = v; }
        else if (s == "--vs") { const char* v = next("--vs"); if (v) { args.vsName = v; args.meshMode = true; } }
        else if (s == "--tex-synth") args.texSynth = true;
        else if (s == "--vsync") args.vsync = true;
        else if (s == "--scene") { const char* v = next("--scene"); if (v) args.scene = v; }
        else if (s == "--limit") { const char* v = next("--limit"); if (v) args.limit = atoi(v); }
        else if (s == "--view") { const char* v = next("--view"); if (v) args.view = v; }
        else if (s == "--scale") { const char* v = next("--scale"); if (v) args.displayScale = (float)atof(v); }
        else if (s == "--spin") { const char* v = next("--spin"); if (v) args.spinDeg = (float)atof(v); }
        else if (s == "--pool") { const char* v = next("--pool"); if (v) args.pool = v; }
        else if (s == "--cam") { const char* v = next("--cam"); if (v) args.camPos = v; }
        else if (s == "--look") { const char* v = next("--look"); if (v) args.camLook = v; }
        else if (s == "--blit-test") args.blitTest = true;
        else if (s == "--norm") args.normalize = true;
        else if (s == "--lift") args.ground = true;
        else if (s == "--no-ground") args.ground = false;
        else if (s == "--sky") args.sky = true;
        else if (s == "--ground-plane") args.groundPlane = true;
        else if (s == "--stats") args.stats = true;
        else if (s == "--no-cull") args.cull = false;
        else if (s == "--no-frustum") args.noFrustum = true;
        else { LOG("[warn] unknown arg %s", s.c_str()); }
    }
    if (args.reps < 1) args.reps = 1;
    if (args.frames < 1) args.frames = 1;
    if (args.captureFrame <= 0) args.captureFrame = args.warmup + 1;
    if (args.displayScale <= 0.0f) args.displayScale = 1.0f;

    std::string dir = exeDir();
    if (args.model.empty()) args.model = dir + "\\..\\work\\assets\\data\\models\\w_ar_duke_01_handguard_04_hi._ft_at_0000000014FA6010.obj";
    if (args.texture.empty()) args.texture = dir + "\\..\\work\\assets\\textures\\textures\\dictionary_at_0000000002263010\\086_clouds_high.dds";

    App a;
    a.sceneMode = !args.scene.empty();
    if (a.sceneMode) {
        if (args.vsName.empty()) args.vsName = "vs_main";
        args.meshMode = true;
    }
    g_cull = (a.sceneMode && args.cull) ? VK_CULL_MODE_BACK_BIT : VK_CULL_MODE_NONE;

    LOG("=== GTA6 engine M4 %s ===", a.sceneMode ? "(scene instances)" : "(single model)");
    std::string err;
    if (!a.sceneMode) {
        if (!loadObj(args.model, a.mesh, err, true, false)) {
            LOG("[fatal] model load failed: %s (%s)", err.c_str(), args.model.c_str());
            return 1;
        }
        LOG("[stage] model loaded: %s", args.model.c_str());
        LOG("[stage] parsed OBJ: %u positions, %u UVs, %d triangulated tris", a.mesh.srcPositions,
            a.mesh.srcUvs, (int)a.mesh.srcFaces);
        if (!loadDds(args.texture, a.texData, err)) {
            LOG("[fatal] texture load failed: %s (%s)", err.c_str(), args.texture.c_str());
            return 1;
        }
        LOG("[stage] texture parsed: %s", args.texture.c_str());
    }

    a.reps = args.reps;
    a.gsMode = args.fsDbg;
    a.hashEmpty = args.hashEmpty;
    a.texSynth = args.texSynth;
    if (!args.psName.empty()) g_psName = args.psName;
    if (!args.vsName.empty()) g_vsName = args.vsName;
    a.meshMode = args.meshMode;
    a.blitTest = args.blitTest;
    a.captureFrame = args.captureFrame;
    a.hinst = GetModuleHandleA(nullptr);
    if (!createWindow(a, args)) return 1;
    if (!initVulkan(a, args)) {
        destroyAll(a);
        return 1;
    }
    if (a.sceneMode) {
        if (!args.camPos.empty()) {
            a.camEye = parseVec3(args.camPos, a.scene.centroid + Vec3(0, 50, 200));
            a.camTarget = parseVec3(args.camLook, a.scene.centroid);
            a.userCam = true;
        }
        computeCamera(a, args);
    }
    LOG("[stage] resources ready, entering render loop (reps=%d, frames=%d)", args.reps, args.frames);


    LARGE_INTEGER freq;
    QueryPerformanceFrequency(&freq);
    int totalFrames = args.warmup + args.frames;
    double measuredMs = 0.0;
    int measured = 0;
    bool haveFirstFrame = false;
    int captureDone = 0;

    while (a.running) {
        MSG msg;
        while (PeekMessageA(&msg, nullptr, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) a.running = false;
            TranslateMessage(&msg);
            DispatchMessageA(&msg);
        }
        if (!a.running) break;

        if (a.resizePending) {
            a.resizePending = false;
            RECT cr;
            GetClientRect(a.hwnd, &cr);
            if (cr.right > 0 && cr.bottom > 0) {
                vkDeviceWaitIdle(a.dev);
                destroySwapchainDependents(a);
                if (!createSwapchain(a, args) || !createSwapchainDependents(a)) {
                    LOG("[fatal] swapchain recreate failed");
                    break;
                }
                LOG("[stage] swapchain recreated %ux%u", a.extent.width, a.extent.height);
            }
            continue;
        }

        uint32_t imageIndex = 0;
        VkResult ar = vkAcquireNextImageKHR(a.dev, a.swapchain, UINT64_MAX, a.semAcquire, VK_NULL_HANDLE,
                                            &imageIndex);
        if (ar == VK_ERROR_OUT_OF_DATE_KHR) {
            a.resizePending = true;
            continue;
        }
        if (ar != VK_SUCCESS && ar != VK_SUBOPTIMAL_KHR) {
            LOG("[fatal] acquire failed %d", (int)ar);
            break;
        }

        vkResetFences(a.dev, 1, &a.fence);
        bool capture = (a.frameIdx == a.captureFrame) || (a.frameIdx == totalFrames);
        if (!recordFrame(a, args, imageIndex, (uint32_t)a.frameIdx, capture)) break;

        VkPipelineStageFlags waitStage = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        si.waitSemaphoreCount = 1;
        si.pWaitSemaphores = &a.semAcquire;
        si.pWaitDstStageMask = &waitStage;
        si.commandBufferCount = 1;
        si.pCommandBuffers = &a.cmd;
        si.signalSemaphoreCount = 1;
        si.pSignalSemaphores = &a.semRender;

        LARGE_INTEGER t0, t1;
        bool timing = a.frameIdx >= args.warmup && a.frameIdx < totalFrames;
        if (timing) QueryPerformanceCounter(&t0);
        LARGE_INTEGER s0, s1;
        QueryPerformanceCounter(&s0);
        VkResult sr = vkQueueSubmit(a.queue, 1, &si, a.fence);
        QueryPerformanceCounter(&s1);
        if (a.frameIdx < 3)
            LOG("[dbg] submit cpu %.2f ms", (double)(s1.QuadPart - s0.QuadPart) * 1000.0 /
                                                (double)freq.QuadPart);
        if (sr != VK_SUCCESS) {
            LOG("[fatal] submit failed %d", (int)sr);
            break;
        }
        vkWaitForFences(a.dev, 1, &a.fence, VK_TRUE, UINT64_MAX);
        if (timing) {
            QueryPerformanceCounter(&t1);
            measuredMs += (double)(t1.QuadPart - t0.QuadPart) * 1000.0 / (double)freq.QuadPart;
            ++measured;
        }

        VkPresentInfoKHR pi{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
        pi.waitSemaphoreCount = 1;
        pi.pWaitSemaphores = &a.semRender;
        pi.swapchainCount = 1;
        pi.pSwapchains = &a.swapchain;
        pi.pImageIndices = &imageIndex;
        VkResult pr = vkQueuePresentKHR(a.queue, &pi);
        if (pr == VK_ERROR_OUT_OF_DATE_KHR || pr == VK_SUBOPTIMAL_KHR) a.resizePending = true;

        if (!haveFirstFrame) {
            haveFirstFrame = true;
            LOG("[stage] first frame drawn");
        }
        if (capture) {
            ++captureDone;
            writeShot(a, args.shot);
        }

        ++a.frameIdx;
        if (a.frameIdx > totalFrames + 1 && captureDone) break;
        if (a.frameIdx > totalFrames + 60) break; // safety
    }

    if (measured > 0) {
        LOG("[perf] %d frames, avg %.3f ms (%.2f FPS), reps=%d, tris/frame=%u", measured,
            measuredMs / measured, measured * 1000.0 / measuredMs, args.reps,
            a.indexCount / 3 * (uint32_t)args.reps);
        LOG("[perf] gpu=%s", a.gpuName);
    }
    if (a.sceneMode) {
        LOG("[perf] scene: instances in file %zu, drawn %u, frustum-culled %u, tris submitted %u, verts "
            "transformed %u, models loaded %zu, draws issued %u, view=%s scale=%.2f cull=%d norm=%d",
            a.scene.instances.size(), a.drawnInstances, a.culledInstances, a.drawnTris, a.drawnVerts,
            a.pool.size(), a.drawnDraws, args.view.c_str(), args.displayScale, (int)args.cull,
            (int)args.normalize);
    }
    if (args.stats) {
        PROCESS_MEMORY_COUNTERS_EX pmc{};
        pmc.cb = sizeof(pmc);
        if (GetProcessMemoryInfo(GetCurrentProcess(), (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
            LOG("[perf] peak working set %.1f MiB, peak paged pool %.1f MiB, page faults %lu",
                pmc.PeakWorkingSetSize / 1048576.0, pmc.QuotaPeakPagedPoolUsage / 1048576.0,
                pmc.PageFaultCount);
        }
    }

    destroyAll(a);
    if (a.hwnd) DestroyWindow(a.hwnd);
    LOG("=== done, exit 0 ===");
    return 0;
}
