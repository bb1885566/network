
import torch
from torch import nn


class DiscriminatorMultiScales(nn.Module):
    """
    Multi-scales discriminators of composed of 3 scales pqmf discriminators refining q bands and one 1 full scale Melgan

    Args:
        q: The number of PMQF bands sent to the discriminators to be refined
    """

    def __init__(self, q: int = 4):
        super().__init__()

        self.q = q

        # PQMF discriminators
        self.pqmf_discriminators = torch.nn.ModuleList()

        # having multiple dilation helps to focus on multiscale structure of bands
        for dila in [1, 2, 3]:
            self.pqmf_discriminators.append(DiscriminatorEBEN(dilation=dila, q=q))

        # MelGAN discriminator
        self.melgan_discriminator = DiscriminatorMelGAN()

    def forward(self, bands, audio):
        """
        Forward pass of the EBEN discriminators module.

        Args:
            bands (torch.Tensor): PQMF bands
            audio (torch.Tensor): corresponding speech signal

        Returns:
            embeddings (List[List[torch.Tensor]]): a list of all embeddings layers of all discriminators
        """
        embeddings = []

        for dis in self.pqmf_discriminators:
            embeddings.append(dis(bands))

        embeddings.append(self.melgan_discriminator(audio))

        return embeddings


class DiscriminatorEBEN(nn.Module):
    """
    EBEN PQMF-bands discriminator
    """

    def __init__(self, dilation=1, q: int = 4):
        super().__init__()

        self.dilation = dilation

        self.discriminator = nn.ModuleList(
            [
                nn.Sequential(
                    nn.ReflectionPad1d(1),
                    normalized_conv1d(
                        q,
                        80,
                        kernel_size=(3,),
                        stride=(1,),
                        padding=(1,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        80,
                        160,
                        kernel_size=(7,),
                        stride=(2,),
                        padding=(3,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        160,
                        320,
                        kernel_size=(7,),
                        stride=(2,),
                        padding=(3,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        320,
                        480,
                        kernel_size=(7,),
                        stride=(2,),
                        padding=(3,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        480,
                        640,
                        kernel_size=(7,),
                        stride=(2,),
                        padding=(3,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        640,
                        960,
                        kernel_size=(7,),
                        stride=(2,),
                        padding=(3,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        960,
                        960,
                        kernel_size=(5,),
                        stride=(1,),
                        padding=(2,),
                        dilation=self.dilation,
                        groups=q,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                normalized_conv1d(
                    960, 1, kernel_size=(3,), stride=(1,), padding=(1,), groups=1
                ),
            ]
        )

    def forward(self, bands):
        embeddings = [bands]
        for module in self.discriminator:
            embeddings.append(module(embeddings[-1]))
        return embeddings


class DiscriminatorMelGAN(nn.Module):
    """
    MelGAN Discriminator
     inspired from https://github.com/seungwonpark/melgan/blob/master/model/discriminator.py
    """

    def __init__(self):
        super().__init__()

        self.discriminator = nn.ModuleList(
            [
                nn.Sequential(
                    nn.ReflectionPad1d(7),
                    normalized_conv1d(
                        in_channels=1, out_channels=16, kernel_size=(15,), stride=(1,)
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        in_channels=16,
                        out_channels=64,
                        kernel_size=(41,),
                        stride=(4,),
                        padding=20,
                        groups=4,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        in_channels=64,
                        out_channels=256,
                        kernel_size=(41,),
                        stride=(4,),
                        padding=20,
                        groups=4,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        in_channels=256,
                        out_channels=1024,
                        kernel_size=(41,),
                        stride=(4,),
                        padding=20,
                        groups=4,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        in_channels=1024,
                        out_channels=1024,
                        kernel_size=(41,),
                        stride=(4,),
                        padding=20,
                        groups=4,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                nn.Sequential(
                    normalized_conv1d(
                        in_channels=1024,
                        out_channels=1024,
                        kernel_size=(5,),
                        stride=(1,),
                        padding=2,
                    ),
                    nn.LeakyReLU(0.2, inplace=True),
                ),
                normalized_conv1d(
                    in_channels=1024, out_channels=1, kernel_size=3, stride=1, padding=1
                ),
            ]
        )

    def forward(self, audio):
        embeddings = [audio]
        for module in self.discriminator:
            embeddings.append(module(embeddings[-1]))
        return embeddings


def normalized_conv1d(*args, **kwargs):
    return nn.utils.weight_norm(nn.Conv1d(*args, **kwargs))


