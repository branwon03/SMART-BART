import React from 'react';
import { Tabs } from 'expo-router';
import { View, Text, Image, StyleSheet } from 'react-native';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        // Hides the bottom tab banner as requested
        tabBarStyle: { display: 'none' }, 
        headerStyle: { 
          backgroundColor: 'black', 
          height: 110 
        },
        headerTitle: () => (
          <View style={styles.headerContainer}>
            <View style={styles.logoBox}>
              <Image 
                source={require('../../assets/images/bart_logo.png')}
                style={styles.logo} 
              />
            </View>
            <Text style={styles.headerText}>Bay Area{"\n"}Rapid Transit</Text>
          </View>
        ),
      }}>
      <Tabs.Screen name="mobile_report" options={{ title: '' }} />
      <Tabs.Screen name="mobile_context" options={{ title: '' }} />
      <Tabs.Screen name="mobile_review" options={{ title: '' }} />
      <Tabs.Screen name="mobile_confirmation" options={{ title: '' }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  headerContainer: { flexDirection: 'row', alignItems: 'center' },
  logoBox: { backgroundColor: 'white', padding: 4, borderRadius: 2 },
  logo: { width: 40, height: 25, resizeMode: 'contain' },
  headerText: { color: 'white', fontSize: 14, fontWeight: 'bold', marginLeft: 10, lineHeight: 16 },
});