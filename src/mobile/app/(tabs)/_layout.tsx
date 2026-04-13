import React from 'react';
import { Tabs, useRouter, usePathname } from 'expo-router';
import { View, Text, Image, StyleSheet, TouchableOpacity } from 'react-native';

export default function TabLayout() {
  const router = useRouter();
  const pathname = usePathname();

  const steps = ['/mobile_report', '/mobile_context', '/mobile_review', '/mobile_confirmation'];
  const currentIndex = steps.indexOf(pathname as string);

  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        tabBarStyle: { display: 'flex' },
        headerStyle: { backgroundColor: 'black', height: 110 },
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
      <Tabs.Screen name="mobile_report" options={{ title: 'report' }} />
      <Tabs.Screen name="mobile_context" options={{ title: 'context' }} />
      <Tabs.Screen name="mobile_confirmation" options={{ title: 'confirm'}} />
      <Tabs.Screen name="mobile_review" options={{ title: 'review'}} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  headerContainer: { flexDirection: 'row', alignItems: 'center' },
  logoBox: { backgroundColor: 'white', padding: 4, borderRadius: 2 },
  logo: { width: 40, height: 25, resizeMode: 'contain' },
  headerText: { color: 'white', fontSize: 14, fontWeight: 'bold', marginLeft: 10, lineHeight: 16 },
});