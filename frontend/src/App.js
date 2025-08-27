import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { Clock, Github, Code, Settings, Bell, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Switch } from "./components/ui/switch";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { useToast } from "./hooks/use-toast";
import { Toaster } from "./components/ui/toaster";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggers, setTriggers] = useState([]);
  const [newTriggerTime, setNewTriggerTime] = useState("23:45");
  const [selectedPlatform, setSelectedPlatform] = useState("github");
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const { toast } = useToast();
  
  // Use the configured GitHub username
  const username = "NK-NiteshKumar";

  useEffect(() => {
    checkNotificationPermission();
    registerServiceWorker();
    fetchDashboard();
    fetchTriggers();
    
    // Set up periodic refresh every 5 minutes
    const interval = setInterval(fetchDashboard, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const registerServiceWorker = async () => {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('Service Worker registered:', registration);
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  };

  const checkNotificationPermission = () => {
    if ('Notification' in window) {
      setNotificationsEnabled(Notification.permission === 'granted');
    }
  };

  const requestNotificationPermission = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setNotificationsEnabled(permission === 'granted');
      
      if (permission === 'granted') {
        toast({
          title: "Notifications Enabled",
          description: "You'll now receive reminder notifications!",
        });
      } else {
        toast({
          title: "Notifications Disabled",
          description: "Enable notifications in your browser settings to receive reminders.",
          variant: "destructive"
        });
      }
    }
  };

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/dashboard/${username}`);
      setDashboardData(response.data);
    } catch (error) {
      console.error("Error fetching dashboard:", error);
      toast({
        title: "Error",
        description: "Failed to fetch dashboard data. Please try again.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchTriggers = async () => {
    try {
      const response = await axios.get(`${API}/triggers/${username}`);
      setTriggers(response.data);
    } catch (error) {
      console.error("Error fetching triggers:", error);
    }
  };

  const createTrigger = async () => {
    try {
      const newTrigger = {
        platform: selectedPlatform,
        username: username,
        trigger_time: newTriggerTime,
        enabled: true
      };
      
      await axios.post(`${API}/triggers`, newTrigger);
      
      toast({
        title: "Trigger Created",
        description: `${selectedPlatform} reminder set for ${newTriggerTime}`,
      });
      
      fetchTriggers();
      setNewTriggerTime("23:45");
    } catch (error) {
      console.error("Error creating trigger:", error);
      toast({
        title: "Error",
        description: "Failed to create trigger. Please try again.",
        variant: "destructive"
      });
    }
  };

  const deleteTrigger = async (triggerId) => {
    try {
      await axios.delete(`${API}/triggers/${triggerId}`);
      
      toast({
        title: "Trigger Deleted",
        description: "Reminder trigger has been removed.",
      });
      
      fetchTriggers();
    } catch (error) {
      console.error("Error deleting trigger:", error);
      toast({
        title: "Error",
        description: "Failed to delete trigger. Please try again.",
        variant: "destructive"
      });
    }
  };

  const showNotification = (title, body, icon) => {
    if (notificationsEnabled && 'Notification' in window) {
      const notification = new Notification(title, {
        body,
        icon: icon || '/favicon.ico',
        badge: '/favicon.ico'
      });
      
      // Auto close after 5 seconds
      setTimeout(() => notification.close(), 5000);
    }
  };

  const testNotification = () => {
    showNotification(
      "🔔 Reminder Test",
      "This is how your reminders will look!",
      "🔔"
    );
  };

  const StatusIcon = ({ status, platform }) => {
    if (loading) return <AlertCircle className="h-5 w-5 text-yellow-500 animate-pulse" />;
    
    if (platform === 'github') {
      return status?.has_commits_today 
        ? <CheckCircle className="h-5 w-5 text-green-500" />
        : <XCircle className="h-5 w-5 text-red-500" />;
    } else {
      return status?.potd_solved 
        ? <CheckCircle className="h-5 w-5 text-green-500" />
        : <XCircle className="h-5 w-5 text-red-500" />;
    }
  };

  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400 mx-auto mb-4"></div>
          <p className="text-purple-200 text-lg">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <Toaster />
      
      {/* Header */}
      <header className="border-b border-purple-800/30 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500">
                <Bell className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Code Tracker</h1>
                <p className="text-purple-200 text-sm">Stay on top of your coding goals</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="bg-purple-800/50 text-purple-200">
                {username}
              </Badge>
              <Button 
                onClick={fetchDashboard} 
                disabled={loading}
                variant="outline"
                className="border-purple-600 text-purple-200 hover:bg-purple-800/50"
              >
                <Clock className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Tabs defaultValue="dashboard" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 bg-black/20 border border-purple-800/30">
            <TabsTrigger value="dashboard" className="data-[state=active]:bg-purple-600">
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-purple-600">
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {/* Platform Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* GitHub Card */}
              <Card className="bg-black/30 border-purple-800/30 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between text-white">
                    <div className="flex items-center space-x-2">
                      <Github className="h-5 w-5 text-purple-400" />
                      <span>GitHub</span>
                    </div>
                    <StatusIcon status={dashboardData?.github} platform="github" />
                  </CardTitle>
                  <CardDescription className="text-purple-200">
                    Daily commit tracking for {username}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboardData?.github ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-purple-200">Commits Today:</span>
                        <Badge 
                          variant={dashboardData.github.has_commits_today ? "default" : "secondary"}
                          className={dashboardData.github.has_commits_today 
                            ? "bg-green-600 text-white" 
                            : "bg-red-600 text-white"
                          }
                        >
                          {dashboardData.github.commit_count}
                        </Badge>
                      </div>
                      
                      {dashboardData.github.commits?.length > 0 && (
                        <div className="mt-4">
                          <p className="text-sm text-purple-300 mb-2">Recent commits:</p>
                          <div className="space-y-2 max-h-32 overflow-y-auto">
                            {dashboardData.github.commits.slice(0, 3).map((commit, idx) => (
                              <div key={idx} className="text-xs bg-purple-900/30 rounded p-2">
                                <p className="text-purple-100 truncate">{commit.message}</p>
                                <p className="text-purple-400 text-xs">{commit.repository}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-purple-300">Loading...</p>
                  )}
                </CardContent>
              </Card>

              {/* LeetCode Card */}
              <Card className="bg-black/30 border-purple-800/30 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between text-white">
                    <div className="flex items-center space-x-2">
                      <Code className="h-5 w-5 text-orange-400" />
                      <span>LeetCode</span>
                    </div>
                    <StatusIcon status={dashboardData?.leetcode} platform="leetcode" />
                  </CardTitle>
                  <CardDescription className="text-purple-200">
                    Problem of the Day tracking
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboardData?.leetcode ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-purple-200">POTD Status:</span>
                        <Badge 
                          variant={dashboardData.leetcode.potd_solved ? "default" : "secondary"}
                          className={dashboardData.leetcode.potd_solved 
                            ? "bg-green-600 text-white" 
                            : "bg-orange-600 text-white"
                          }
                        >
                          {dashboardData.leetcode.potd_solved ? "Solved" : "Pending"}
                        </Badge>
                      </div>
                      
                      <div className="mt-4 space-y-2">
                        <p className="text-sm font-medium text-purple-100">
                          {dashboardData.leetcode.potd_title}
                        </p>
                        <div className="flex justify-between text-xs">
                          <span className="text-purple-300">Difficulty:</span>
                          <Badge 
                            variant="outline" 
                            className={`border-${dashboardData.leetcode.potd_difficulty === 'Easy' ? 'green' : 
                              dashboardData.leetcode.potd_difficulty === 'Medium' ? 'orange' : 'red'}-400`}
                          >
                            {dashboardData.leetcode.potd_difficulty}
                          </Badge>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-purple-300">Date:</span>
                          <span className="text-purple-100">{dashboardData.leetcode.potd_date}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-purple-300">Loading...</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Last Updated */}
            {dashboardData && (
              <Card className="bg-black/20 border-purple-800/30">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <span className="text-purple-200 text-sm">Last updated:</span>
                    <span className="text-purple-100 text-sm">
                      {new Date(dashboardData.last_updated).toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="settings" className="space-y-6">
            {/* Notification Settings */}
            <Card className="bg-black/30 border-purple-800/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Notification Settings</CardTitle>
                <CardDescription className="text-purple-200">
                  Configure when and how you want to receive reminders
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="notifications" className="text-purple-200">
                    Enable Browser Notifications
                  </Label>
                  <Switch
                    id="notifications"
                    checked={notificationsEnabled}
                    onCheckedChange={requestNotificationPermission}
                  />
                </div>
                
                {notificationsEnabled && (
                  <Button 
                    onClick={testNotification} 
                    variant="outline"
                    className="w-full border-purple-600 text-purple-200 hover:bg-purple-800/50"
                  >
                    Test Notification
                  </Button>
                )}
              </CardContent>
            </Card>

            {/* Add New Trigger */}
            <Card className="bg-black/30 border-purple-800/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Add Reminder</CardTitle>
                <CardDescription className="text-purple-200">
                  Set up new reminder triggers for your coding activities
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="platform" className="text-purple-200">Platform</Label>
                    <select 
                      id="platform"
                      value={selectedPlatform}
                      onChange={(e) => setSelectedPlatform(e.target.value)}
                      className="w-full mt-1 p-2 bg-black/30 border border-purple-600 rounded-md text-purple-100"
                    >
                      <option value="github">GitHub</option>
                      <option value="leetcode">LeetCode</option>
                    </select>
                  </div>
                  
                  <div>
                    <Label htmlFor="time" className="text-purple-200">Reminder Time</Label>
                    <Input
                      id="time"
                      type="time"
                      value={newTriggerTime}
                      onChange={(e) => setNewTriggerTime(e.target.value)}
                      className="bg-black/30 border-purple-600 text-purple-100"
                    />
                  </div>
                  
                  <div className="flex items-end">
                    <Button 
                      onClick={createTrigger} 
                      className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                    >
                      Add Reminder
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Active Triggers */}
            <Card className="bg-black/30 border-purple-800/30 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-white">Active Reminders</CardTitle>
                <CardDescription className="text-purple-200">
                  Your scheduled reminder notifications
                </CardDescription>
              </CardHeader>
              <CardContent>
                {triggers.length > 0 ? (
                  <div className="space-y-2">
                    {triggers.map((trigger) => (
                      <div 
                        key={trigger.id} 
                        className="flex items-center justify-between p-3 bg-purple-900/30 rounded-lg"
                      >
                        <div className="flex items-center space-x-3">
                          {trigger.platform === 'github' ? (
                            <Github className="h-4 w-4 text-purple-400" />
                          ) : (
                            <Code className="h-4 w-4 text-orange-400" />
                          )}
                          <div>
                            <p className="text-purple-100 font-medium capitalize">
                              {trigger.platform}
                            </p>
                            <p className="text-purple-300 text-sm">
                              Daily at {trigger.trigger_time}
                            </p>
                          </div>
                        </div>
                        
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteTrigger(trigger.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-purple-300 text-center py-4">
                    No reminders set up yet. Add one above to get started!
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;