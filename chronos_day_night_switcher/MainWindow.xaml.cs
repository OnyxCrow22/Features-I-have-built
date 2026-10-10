using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Net.Http;
using System.Text.Json;
using Innovative.SolarCalculator;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Toolkit.Uwp.Notifications;
using Windows.UI.Notifications;

namespace Chronos_Day_and_Night_Switcher
{

    public partial class MainWindow : Window
    {
        private readonly ApplicationSettings _settings = new();
        private readonly ThemeScheduler _scheduler;

        public MainWindow()
        {
            InitializeComponent();

            this.Hide();

            _scheduler = new ThemeScheduler(_settings);
            _ = _scheduler.StartAsync();
        }

        public void OnAutomaticResume(object sendMessage, RoutedEventArgs clicked)
        {
            _settings.ALLOW_MANUAL_OVERRIDE = null;
            ThemeScheduler.ShowNotification(
                "Manual Override Disabled", 
                "The system and app theme will now changed automatically based on the time of day.");
        }

        public void OnAppThemeChange(object sendMessage, RoutedEventArgs clicked)
        {
            if (sendMessage is MenuItem menuItem)
                _settings.CHANGE_APP_THEME = menuItem.IsChecked;
        }

        public void OnSystemThemeChange(object sendMessage, RoutedEventArgs clicked)
        {
            if (sendMessage is MenuItem menuItem)
                _settings.CHANGE_SYSTEM_THEME = menuItem.IsChecked;
        }

        public void OnForceLightClick(object sendMessage, RoutedEventArgs clicked)
        {
            _settings.ALLOW_MANUAL_OVERRIDE = false; // Turn off manual switches
            ThemeManager.SetTheme(isDark: false, _settings.CHANGE_APP_THEME, _settings.CHANGE_SYSTEM_THEME);
            ThemeScheduler.ShowNotification("The light mode has been changed.", "It has now changed from dark to light");
        }

        public void OnForceDarkClick(object sendMessage, RoutedEventArgs clicked)
        {
            _settings.ALLOW_MANUAL_OVERRIDE = true; // Turn on manual switches
            ThemeManager.SetTheme(isDark: true, _settings.CHANGE_APP_THEME, _settings.CHANGE_SYSTEM_THEME);
            ThemeScheduler.ShowNotification("The light mode has been changed.", "It has now changed from light to dark");
        }

        public void OnTerminationClick(object sendMessage, RoutedEventArgs clicked)
        {
            _scheduler.Stop();
            Application.Current.Shutdown();
        }
    }

    public static class TimeZones
    {
        public static readonly IReadOnlyDictionary<double, (double Latitude, double Longitude)> Capitals =
            new Dictionary<double, (double Latitude, double Longitude)>
            {
                { -12.0, (0.193635, -176.476894) }, // Baker Island
                { -11.0, (-13.848202, -171.760454) }, // Apia, Independent State of Samoa
                { -10.0, (21.301821, -157.858052) }, // Honolulu, Hawai'i
                { -9.5, (8.54424, 140.06135) }, // Taioha'e, French Polynesia
                { -9.0, (58.301986, -134.418464) }, // Juneau, Alaska
                { -8.0, (38.571181, -121.489869) }, // Sacramento, California
                { -7.0, (39.741834, -104.997956) }, // Denver, Colorado
                { -6.0, (30.270916, -97.741936) }, // Austin, Texas
                { -5.0, (37.544046, -77.441989) }, // Richmond, Virginia
                { -4.0, (44.645680, -63.614636) }, // Halifax, Nova Scotia
                { -3.5, (47.547054, -52.740050) }, // Saint John's, Newfoundland and Labrador
                { -3.0, (-15.803536, -47.891805)}, // Brasilia, Federal District, Federative Republic of Brazil
                { -2.0, (64.174579, -51.731977) }, // Nuuk, Greenland
                { -1.0, (14.914903, -23.510122) }, // Praia, Republic of Cabo Verde
                { 0, (51.507188, -0.127841) }, // London, England
                { +1.0, (50.844518, 4.352950) }, // Brussels-Capital Region, Kingdom of Belgium
                { +2.0, (52.31102, 13.24239) }, // Berlin, Federal Republic of Germany
                { +3.0, (37.59030, 23.43398)}, // Athens, Hellenic Republic
                { +3.5, (35.43227, 51.19568) }, // Tehran, Islamic Republic of Iran
                { +4.0, (24.27138, 54.22426) }, // Abu Dhabi, United Arab Emirates
                { +4.5, (34.33186, 69.12249) }, // Kabul, Islamic Emirate of Afghanistan
                { +5.0, (33.41572, 73.02130) }, // Islamabad, Islamic Republic of Pakistan
                { +5.5, (28.36487, 77.12310) }, // National Capital Territory of Delhi, Republic of India
                { +5.75, (27.42431, 85.19101) }, // Kathmandu Metropolitan City, Federal Democractic Republic of Nepal
                { +6.0, (23.48144, 90.24522) }, // Dhaka, People's Republic of Bangladesh
                { +6.5, (19.45451, 96.04436) }, // Nay Pyi Taw, Republic of the Union of Myanmar
                { +7.0, (13.45201, 100.30180) }, // Krung Thep Maha Nakhon (Bangkok), Kingdom of Thailand
                { +8.0, (39.51186, 116.20374) }, // Beijing, People's Republic of China
                { +8.75, (-31.40347, 128.53170) }, // Ecula, Western Australia, Commonwealth of Australia
                { +9.0, (35.39378, 139.45462) }, // Tokyo Metropolis, Japan
                { +9.5,  (-12.27535, 130.50413) }, // Darwin, Northern Territory, Commonwealth of Australia
                { +10.0, (-27.27485, 153.01100) }, // Meanjin (Brisbane), Queensland, Commonwealth of Australia
                { +10.5, (-34.55401, 138.35110) }, // Tamdanya (Adelaide), South Australia, Commonwealth of Australia
                { +11.0, (-22.16292, 166.26224) }, // Nouméa, New Caledonia
                { +12.0, (-18.07376, 178.26440) }, // Suva, Republic of Fiji
                { +12.75, (-43.57072, 176.33328) }, // Waiteki (Waitangi), Wharekuri (Chatham Islands Territory)
                { +13.0, (-41.17136, 174.46432) }, // Te Whanganui-a-Tara (Wellington), Aoteraroa (New Zealand)
                { +14.0,  (1.58525, -157.28417)}, // London, Republic of Kiribati
            };

        public static (double latitude, double longitude) GetFallbackLocation()
        {
            double UTCOffset = TimeZoneInfo.Local.GetUtcOffset(DateTime.Now).TotalHours;

            if (Capitals.TryGetValue(UTCOffset, out var location))
            {
                return location;
            }

            return (51.507188, -0.127841); // Default to London, England when in doubt.
        }
    }

    public class ApplicationSettings()
    {
        public int CHECK_INTERVAL_SECONDS { get; set; } = 60;
        public bool CHANGE_APP_THEME { get; set; } = true;
        public bool CHANGE_SYSTEM_THEME { get; set; } = true;
        public bool? ALLOW_MANUAL_OVERRIDE { get; set; } = null;
        public bool HAS_SEEN_DAYNOTIFICATION { get; set; } = false;
        public bool HAS_SEEN_NIGHTNOTIFICATION { get; set; } = false;
    }

    public static class GetLocationService
    {
        private static readonly HttpClient userClient = new();

        public static async Task<(double Latitude, double Longitude)?> GetCurrentLocation()
        {
            try
            {
                string queryJSONResponse = await userClient.GetStringAsync("http://ip-api.com/json/?fields=status,lat,lon");
                using JsonDocument locationDocument = JsonDocument.Parse(queryJSONResponse);
                JsonElement parentRoot = locationDocument.RootElement;

                if (parentRoot.GetProperty("status").GetString() == "success")
                {
                    double lat = parentRoot.GetProperty("lat").GetDouble();
                    double lon = parentRoot.GetProperty("lon").GetDouble();
                    return (lat, lon);
                }
            }
            catch
            {
                // Fall back if user is offline...
            }

            return null;
        }
    }

    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    /// 
    public static class ThemeManager
    {
        private const string RegistryPath = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize";
        private const int HWND_BROADCAST = 0xffff;
        private const uint WM_SETTINGCHANGE = 0x001A;
        private const UIntPtr SMTO_ABORTIFHUNG = (UIntPtr)0x0002;

        /// <summary>
        /// Determines how long the user has before the message times out.
        /// </summary>
        /// <param name="hWnd"></param>
        /// <param name="Message"></param>
        /// <param name="WindowsParameter"></param>
        /// <param name="lParameter"></param>
        /// <param name="flags"></param>
        /// <param name="messageTimeout"></param>
        /// <param name="result"></param>
        /// <returns></returns>

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr SendMessageTimeout(
            IntPtr hWnd,
            uint Message,
            UIntPtr WindowsParameter,
            string lParameter,
            UIntPtr flags,
            uint messageTimeout,
            out UIntPtr result);

        public static void SetTheme(bool isDark, bool changeApps = true, bool changeSystem = true)
        {
            int value = isDark ? 0 : 1;

            using (RegistryKey? regKey = Registry.CurrentUser.OpenSubKey(RegistryPath, writable: true))
            {
                if (regKey != null)
                {
                    if (changeApps) regKey.SetValue("AppsUseLightTheme", value, RegistryValueKind.DWord);
                    if (changeSystem) regKey.SetValue("SystemUsesLightTheme", value, RegistryValueKind.DWord);
                }
            }

            SendMessageTimeout(
                (IntPtr)HWND_BROADCAST,
                WM_SETTINGCHANGE,
                UIntPtr.Zero,
                "ImmersiveColorSet",
                SMTO_ABORTIFHUNG,
                5000,
                out _);
        }
    }

    /// <summary>
    /// Calculates the sunrise and sunset time based on the users position.
    /// </summary>
    public static class SolarEngine
    {
        public static (DateTime Sunrise, DateTime sunset) GetSunTime(double latitude, double longitude, DateTime? targetDate = null)
        {
            DateTime currentDate = targetDate?.Date ?? DateTime.Today; // Get today's date.

            SolarTimes solTimes = new(currentDate, latitude, longitude);

            DateTime sunriseTime = solTimes.Sunrise.ToLocalTime(); // Find the local time of sunrise.
            DateTime sunsetTime = solTimes.Sunset.ToLocalTime(); // Find the local time of sunset.

            if (sunsetTime < sunriseTime)
                sunsetTime = sunsetTime.AddDays(1); // One day added to the count.

            return (sunriseTime, sunsetTime);
        }
    }

    /// <summary>
    /// Find the requested file.
    /// </summary>
    public static class ResourceCollector
    {
        public static string GetResourcePath(string resourcePath)
        {
            string baseDirectory = AppDomain.CurrentDomain.BaseDirectory;
            return Path.Combine(baseDirectory, resourcePath);
        }

        /// <summary>
        /// Search for the requested image
        /// </summary>
        /// <param name="resourcePath"></param>
        /// <returns></returns>
        public static Uri GetImage(string resourcePath)
        {
            return new Uri($"pack://application:,,,/{resourcePath.TrimStart('/')}", UriKind.Absolute);
        }
    }

    public class ThemeScheduler
    {
        private readonly PeriodicTimer _timer = new(TimeSpan.FromMinutes(1));
        private readonly ApplicationSettings _settings;
        private readonly CancellationTokenSource _cts = new();

        private (double latitude, double longitude)? _cachedLocation = null;
        private DateTime _lastLocationCheckElapsed = DateTime.MinValue;
        private readonly TimeSpan _locationRefreshInterval = TimeSpan.FromHours(2);

        private bool? _currentLightDark = null;

        public ThemeScheduler(ApplicationSettings settings) => _settings = settings;

        public async Task StartAsync()
        {
            await EvaluateSwitchThemeAsync();

            try
            {
                while (await _timer.WaitForNextTickAsync(_cts.Token))
                {
                    await EvaluateSwitchThemeAsync();
                }
            }
            catch (OperationCanceledException OCE)
            {
                // Shutdown gracefully.
            }
        }

        private async Task EvaluateSwitchThemeAsync()
        {
            if (_settings.ALLOW_MANUAL_OVERRIDE.HasValue)
            {
                bool forcedDarkness = _settings.ALLOW_MANUAL_OVERRIDE.Value;
                if (_currentLightDark != forcedDarkness)
                {
                    _currentLightDark = forcedDarkness;
                    ThemeManager.SetTheme(forcedDarkness, _settings.CHANGE_APP_THEME, _settings.CHANGE_SYSTEM_THEME);
                }
                return;
            }

            if (_cachedLocation == null || (DateTime.Now - _lastLocationCheckElapsed) > _locationRefreshInterval)
            {
                var IPLocation = await GetLocationService.GetCurrentLocation();
                _cachedLocation = IPLocation ?? TimeZones.GetFallbackLocation();
                _lastLocationCheckElapsed = DateTime.Now;
            }

            var (latitude, longitude) = _cachedLocation.Value;

            var (sunrise, sunset) = SolarEngine.GetSunTime(latitude, longitude);
            DateTime currentTime = DateTime.Now;

            bool shouldBeDark = currentTime < sunrise || currentTime > sunset;

            if (_currentLightDark != shouldBeDark)
            {
                _currentLightDark = shouldBeDark;
                ThemeManager.SetTheme(shouldBeDark, _settings.CHANGE_APP_THEME, _settings.CHANGE_SYSTEM_THEME);

                string formattedTime = DateTime.Now.ToShortTimeString();

                if (shouldBeDark && !_settings.HAS_SEEN_NIGHTNOTIFICATION)
                {
                    var (title, message) = GetNotificationGreeting(isDark: true, currentTime.Hour);
                    ShowNotification(title, message);

                    _settings.HAS_SEEN_NIGHTNOTIFICATION = true;
                    _settings.HAS_SEEN_DAYNOTIFICATION = false;
                }
                else if (!shouldBeDark && !_settings.HAS_SEEN_DAYNOTIFICATION)
                {
                    var (title, message) = GetNotificationGreeting(isDark: false, currentTime.Hour);
                    ShowNotification(title, message);

                    _settings.HAS_SEEN_DAYNOTIFICATION = true;
                    _settings.HAS_SEEN_NIGHTNOTIFICATION = false;
                }
            }
        }

        private static (String title, string message) GetNotificationGreeting(bool isDark, int hour)
        {
            string formattedTime = DateTime.Now.ToShortTimeString();

            if (!isDark)
            {
                if (hour >= 12)
                {
                    return ("Good afternoon!",
                            $"The theme has been set to the light theme, as it is {formattedTime}! Have a good afternoon :)");
                }

                return ("Good morning!",
                    $"The theme has been set to the light theme, as it is {formattedTime}! Have a good morning! :)");
            }
            else
            {
                if (hour >= 19)
                {
                    return ("Good night!",
                        $"The theme has been set to the dark theme, as it is {formattedTime}! Have a good night! :)");
                }
                if (hour >= 16)
                {
                    return ("Good evening!",
                        $"The theme has been set to the dark theme, as it is {formattedTime}! Have a good evening!! :)");
                }

                return ("Good night!",
                        $"The theme has been set to the dark theme, as it is {formattedTime}! Have a good night! :)");
            }
        }

        public void Stop() => _cts.Cancel();

        public static void ShowNotification(string title, string message)
        {
            new ToastContentBuilder()
                .AddText(title)
                .AddText(message)
                .Show();
        }
    }
}