"use client"

import type { ChatSettings } from "@/lib/chat-data"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"

interface SettingsDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  settings: ChatSettings
  onSettingsChange: (settings: ChatSettings) => void
}

export function SettingsDrawer({
  open,
  onOpenChange,
  settings,
  onSettingsChange,
}: SettingsDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-80">
        <SheetHeader>
          <SheetTitle>Chat Settings</SheetTitle>
          <SheetDescription>
            Customize how responses are delivered.
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-6 px-4 py-2">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="gentle-tone" className="text-sm font-medium">
                Gentle tone
              </Label>
              <p className="text-xs text-muted-foreground">
                Responses feel warm, non-judgmental
              </p>
            </div>
            <Switch
              id="gentle-tone"
              checked={settings.gentleTone}
              onCheckedChange={(checked) =>
                onSettingsChange({ ...settings, gentleTone: checked })
              }
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label htmlFor="detailed-answers" className="text-sm font-medium">
                Detailed answers
              </Label>
              <p className="text-xs text-muted-foreground">
                Longer, more thorough responses
              </p>
            </div>
            <Switch
              id="detailed-answers"
              checked={settings.detailedAnswers}
              onCheckedChange={(checked) =>
                onSettingsChange({ ...settings, detailedAnswers: checked })
              }
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
