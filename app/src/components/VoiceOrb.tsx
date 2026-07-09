import React, { useEffect, useRef } from "react";
import { Animated, Easing, Pressable, StyleSheet, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { colors } from "../theme";
import type { VoiceState } from "../hooks/useVoice";

interface Props {
  state: VoiceState;
  onPress: () => void;
}

const ORB_SIZE = 92;

/**
 * The pulsing voice orb — Sarathi's single point of command.
 * idle: slow brass breathing · listening: quick pulse + expanding halo ·
 * processing: steady shimmer while Claude works.
 */
export function VoiceOrb({ state, onPress }: Props) {
  const breathe = useRef(new Animated.Value(0)).current;
  const halo = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    breathe.setValue(0);
    const duration = state === "listening" ? 700 : state === "processing" ? 450 : 2400;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breathe, {
          toValue: 1,
          duration,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.timing(breathe, {
          toValue: 0,
          duration,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [state, breathe]);

  useEffect(() => {
    halo.setValue(0);
    if (state !== "listening") return;
    const loop = Animated.loop(
      Animated.timing(halo, {
        toValue: 1,
        duration: 1500,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      })
    );
    loop.start();
    return () => loop.stop();
  }, [state, halo]);

  const scale = breathe.interpolate({
    inputRange: [0, 1],
    outputRange: [1, state === "idle" ? 1.05 : 1.12],
  });
  const haloScale = halo.interpolate({ inputRange: [0, 1], outputRange: [1, 2.1] });
  const haloOpacity = halo.interpolate({ inputRange: [0, 0.15, 1], outputRange: [0, 0.45, 0] });

  const gradient: readonly [string, string, ...string[]] =
    state === "processing"
      ? [colors.inkRaised2, colors.brassDeep]
      : state === "listening"
        ? [colors.brassBright, colors.brassDeep]
        : [colors.brass, colors.brassDeep];

  return (
    <View style={styles.wrap} pointerEvents="box-none">
      <Animated.View
        style={[
          styles.halo,
          { opacity: haloOpacity, transform: [{ scale: haloScale }] },
        ]}
      />
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={
          state === "listening" ? "Stop listening" : "Ask Sarathi"
        }
        onPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          onPress();
        }}
      >
        <Animated.View style={{ transform: [{ scale }] }}>
          <LinearGradient
            colors={gradient}
            start={{ x: 0.2, y: 0.1 }}
            end={{ x: 0.8, y: 1 }}
            style={styles.orb}
          >
            <View style={styles.innerRing}>
              <View style={styles.core} />
            </View>
          </LinearGradient>
        </Animated.View>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", justifyContent: "center" },
  halo: {
    position: "absolute",
    width: ORB_SIZE,
    height: ORB_SIZE,
    borderRadius: ORB_SIZE / 2,
    borderWidth: 1.5,
    borderColor: colors.brassBright,
  },
  orb: {
    width: ORB_SIZE,
    height: ORB_SIZE,
    borderRadius: ORB_SIZE / 2,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.brass,
    shadowOpacity: 0.55,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 6 },
    elevation: 12,
  },
  innerRing: {
    width: ORB_SIZE - 18,
    height: ORB_SIZE - 18,
    borderRadius: (ORB_SIZE - 18) / 2,
    borderWidth: 1,
    borderColor: "rgba(11, 21, 36, 0.35)",
    alignItems: "center",
    justifyContent: "center",
  },
  core: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: colors.ink,
    opacity: 0.85,
  },
});
