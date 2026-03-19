"use client"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { MessageCircle, Lightbulb, Compass } from "lucide-react"

interface HowItWorksDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function HowItWorksDialog({
  open,
  onOpenChange,
}: HowItWorksDialogProps) {
  const steps = [
    {
      icon: <MessageCircle className="size-6" />,
      title: "Ask",
      description:
        "Type any question about faith, life, prayer, purpose, or anything on your heart. There are no silly questions here.",
    },
    {
      icon: <Lightbulb className="size-6" />,
      title: "Reflect",
      description:
        "Receive a thoughtful, compassionate response with relevant Bible passages and themes to help you think deeper.",
    },
    {
      icon: <Compass className="size-6" />,
      title: "Explore",
      description:
        "Follow up with more questions, save helpful responses, or browse our topic guides to continue your journey.",
    },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">How it works</DialogTitle>
          <DialogDescription>
            A simple, safe space to explore your questions.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-6 mt-2">
          {steps.map((step, i) => (
            <div key={step.title} className="flex items-start gap-4">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                {step.icon}
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-foreground">
                  {`${i + 1}. ${step.title}`}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-xl bg-muted/50 border border-border p-4">
          <p className="text-xs leading-relaxed text-muted-foreground">
            <span className="font-semibold text-foreground">Please note:</span>{" "}
            This chatbot offers faith-based guidance inspired by the Alpha
            Course approach. It is not a substitute for professional counseling,
            pastoral care, or emergency services. If you are in crisis, please
            reach out to a crisis helpline in your area.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
