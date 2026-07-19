import { ref, onMounted, onUnmounted } from 'vue'

// 与全局 CSS 断点保持一致：手机 <768，平板 768–1023，桌面 ≥1024
const MOBILE_MQ = '(max-width: 767px)'
const TABLET_MQ = '(min-width: 768px) and (max-width: 1023px)'

export function useBreakpoint() {
  const mqMobile = window.matchMedia(MOBILE_MQ)
  const mqTablet = window.matchMedia(TABLET_MQ)

  // 同步读初值：matchMedia 反映真实媒体状态，和 CSS 断点一致，比 onMounted 里再读 innerWidth 更可靠
  const isMobile = ref(mqMobile.matches)
  const isTablet = ref(mqTablet.matches)

  function update() {
    isMobile.value = mqMobile.matches
    isTablet.value = mqTablet.matches
  }

  // 断点变化时实时更新（含 DevTools 设备模式切换宽度）
  mqMobile.addEventListener('change', update)
  mqTablet.addEventListener('change', update)

  onMounted(() => {
    // 兜底：DevTools 设备模式刷新时，模拟视口可能在挂载后才生效、且不触发任何事件，
    // 这里挂载后立即 + 两次延迟各同步一次，纠正初值偏差。
    update()
    requestAnimationFrame(update)
    setTimeout(update, 250)
  })

  onUnmounted(() => {
    mqMobile.removeEventListener('change', update)
    mqTablet.removeEventListener('change', update)
  })

  return { isMobile, isTablet }
}
